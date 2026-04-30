const message = [
  'Legacy Express backend is quarantined and must not be started by default.',
  'Use the canonical FastAPI service instead:',
  'uvicorn src.api.fastapi_app:app --host 0.0.0.0 --port 8000'
].join('\n');

console.error(message);
process.exit(1);
