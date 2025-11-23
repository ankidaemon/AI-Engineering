import 'dotenv/config';
import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import { router as demoRouter } from './routes/demo.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
app.use(express.json({ limit: '1mb' }));

app.get('/health', (_req, res) => {
  res.json({ ok: true });
});

// Only demo routes for prompt engineering techniques
app.use('/v1/demo', demoRouter);

// Serve static files from the public directory
app.use(express.static(path.join(__dirname, '../public')));

// Serve the React app for any non-API routes
app.get('*', (_req, res) => {
  res.sendFile(path.join(__dirname, '../public/index.html'));
});

// global error handler
app.use((err: any, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  console.error('Unhandled error:', err);
  res.status(500).json({ error: 'internal_error', message: err?.message || 'Unknown error' });
});

const PORT = process.env.PORT ? Number(process.env.PORT) : 3000;
app.listen(PORT, () => {
  console.log(`[server] Prompt Engineering Demo listening on http://localhost:${PORT}`);
});
