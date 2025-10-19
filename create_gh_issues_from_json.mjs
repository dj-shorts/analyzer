// create_gh_issues_from_json.mjs
// Node 18+ (uses global fetch), no external deps.
//
// Usage:
//   node scripts/create_gh_issues_from_json.mjs \
//     --repo owner/repo \
//     --token $GITHUB_TOKEN \
//     --file BACKLOG_MVP_ANALYZER.json \
//     [--labels "area:analyzer,type:feature"] \
//     [--project-id <PROJECT_V2_NODE_ID>] \
//     [--dry-run]
//
// Notes:
// - If --project-id is provided (Projects v2 GraphQL node ID), each created issue
//   will be added to that project via GraphQL `addProjectV2ItemById`.
// - JSON format is the one we generated: { "issues": [ { title, body, labels[], epic, priority, estimate_days, dependencies[] }, ... ] }
// - The script prints created issue numbers (or would-be titles in --dry-run).

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const key = a.slice(2);
      const val = (i + 1 < argv.length && !argv[i + 1].startsWith('--')) ? argv[++i] : true;
      args[key] = val;
    }
  }
  return args;
}

async function restCreateIssue({ owner, repo, token, title, body, labels }) {
  const res = await fetch(`https://api.github.com/repos/${owner}/${repo}/issues`, {
    method: 'POST',
    headers: { 
      'Authorization': `Bearer ${token}`,
      'Accept': 'application/vnd.github+json',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ title, body, labels })
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Issue create failed: ${res.status} ${txt}`);
  }
  const data = await res.json();
  return { number: data.number, node_id: data.node_id, html_url: data.html_url };
}

async function gqlAddToProject({ token, projectId, contentId }) {
  const query = `
    mutation($projectId:ID!, $contentId:ID!) {
      addProjectV2ItemById(input: { projectId: $projectId, contentId: $contentId }) {
        item { id }
      }
    }
  `;
  const res = await fetch('https://api.github.com/graphql', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      'Accept': 'application/vnd.github+json'
    },
    body: JSON.stringify({ query, variables: { projectId, contentId } })
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`GraphQL failed: ${res.status} ${txt}`);
  }
  const data = await res.json();
  if (data.errors) {
    throw new Error(`GraphQL errors: ${JSON.stringify(data.errors)}`);
  }
  return data.data.addProjectV2ItemById?.item?.id ?? null;
}

async function main() {
  const args = parseArgs(process.argv);
  const repoStr = args.repo;
  const token = args.token || process.env.GITHUB_TOKEN;
  const file = args.file;
  const extraLabels = (args.labels ? args.labels.split(',').map(s => s.trim()).filter(Boolean) : []);
  const projectId = args['project-id'] || null;
  const dryRun = !!args['dry-run'];

  if (!repoStr || !token || !file) {
    console.error('Missing required args. See header for usage.');
    process.exit(2);
  }
  const [owner, repo] = repoStr.split('/');
  const payload = JSON.parse(await (await import('node:fs/promises')).readFile(file, 'utf-8'));
  const issues = payload.issues ?? [];
  if (!Array.isArray(issues) || issues.length === 0) {
    console.error('No issues found in JSON.');
    process.exit(3);
  }

  for (const it of issues) {
    const labels = Array.from(new Set([...(it.labels || []), ...extraLabels]));
    const footer = `\\n\\n**Epic:** ${it.epic}\\n**Priority:** ${it.priority}\\n**Estimate:** ${it.estimate_days}d\\n**Dependencies:** ${(it.dependencies||[]).join(', ')}`;
    const title = it.title;
    const body = (it.body || '') + footer;

    if (dryRun) {
      console.log(`[DRY] would create: ${title} | labels=${labels.join(',')}`);
      continue;
    }

    const { number, node_id, html_url } = await restCreateIssue({ owner, repo, token, title, body, labels });
    console.log(`#${number} ${html_url}`);

    if (projectId) {
      try {
        const itemId = await gqlAddToProject({ token, projectId, contentId: node_id });
        console.log(`  ↳ added to ProjectV2 itemId=${itemId}`);
      } catch (e) {
        console.warn(`  ! project add failed: ${e.message}`);
      }
    }
  }
}

main().catch(err => { console.error(err); process.exit(1); });
