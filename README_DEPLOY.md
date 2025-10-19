# Deploy Notes — AWS S3 + CloudFront + Workers/Analyzer

## S3/CloudFront
- ENV: `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET`, `S3_PREFIX`, `CLOUDFRONT_DOMAIN?`
- Используйте **OAC** для CloudFront → S3, запретите публичные ACL/Policy на бакете.
- Для приватного доступа — короткие **S3 presigned GET**; либо подпись CloudFront URLs.

### Пример (Node.js, AWS SDK v3)
```ts
import { S3Client, PutObjectCommand, GetObjectCommand } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';
const s3 = new S3Client({ region: process.env.AWS_REGION });

export async function presignPut(Key: string, ContentType: string, expiresSec = 3600) {
  const cmd = new PutObjectCommand({ Bucket: process.env.S3_BUCKET, Key, ContentType });
  return getSignedUrl(s3, cmd, { expiresIn: expiresSec });
}

export async function presignGet(Key: string, expiresSec = 3600) {
  const cmd = new GetObjectCommand({ Bucket: process.env.S3_BUCKET, Key });
  return getSignedUrl(s3, cmd, { expiresIn: expiresSec });
}
```

## Analyzer вызов из воркеров
- Запускайте CLI через `child_process.spawn`, стримьте **stdout** с JSON‑ивентами → проксируйте в **SSE**.
- На `cancel` — убивайте дерево процессов (ffmpeg/yt‑dlp).

## Ротация данных
- inputs: хранить 7 дней; outputs: 30 дней (настроить **S3 Lifecycle**).
- Рассмотреть **Intelligent‑Tiering** при длительном хранении архивов.

## Безопасность
- Скан CVE в CI для `ffmpeg`, `yt-dlp`, Python/Node зависимостей.
- Минимизируйте права AWS‑пользователя (IAM policy только на нужные S3 действия).
