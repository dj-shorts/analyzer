// find_project_id.mjs
// Script to find PROJECT_ID for "MVP Analyzer" project

async function findProjectId(token) {
  const query = `
    query {
      organization(login: "dj-shorts") {
        projectsV2(first: 20) {
          nodes {
            id
            title
            url
          }
        }
      }
    }
  `;

  const response = await fetch('https://api.github.com/graphql', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query })
  });

  if (!response.ok) {
    throw new Error(`GraphQL request failed: ${response.status}`);
  }

  const data = await response.json();
  
  if (data.errors) {
    throw new Error(`GraphQL errors: ${JSON.stringify(data.errors)}`);
  }

  const projects = data.data.organization.projectsV2.nodes;
  const mvpAnalyzer = projects.find(project => 
    project.title.toLowerCase().includes('mvp analyzer') || 
    project.title.toLowerCase().includes('analyzer')
  );

  if (mvpAnalyzer) {
    console.log(`Found project: "${mvpAnalyzer.title}"`);
    console.log(`PROJECT_ID: ${mvpAnalyzer.id}`);
    console.log(`URL: ${mvpAnalyzer.url}`);
    return mvpAnalyzer.id;
  } else {
    console.log('Available projects:');
    projects.forEach(project => {
      console.log(`- "${project.title}" (ID: ${project.id})`);
    });
    return null;
  }
}

// Get token from command line or environment
const token = process.argv[2] || process.env.GITHUB_TOKEN;

if (!token) {
  console.error('Usage: node find_project_id.mjs <GITHUB_TOKEN>');
  console.error('Or set GITHUB_TOKEN environment variable');
  process.exit(1);
}

findProjectId(token).catch(err => {
  console.error('Error:', err.message);
  process.exit(1);
});
