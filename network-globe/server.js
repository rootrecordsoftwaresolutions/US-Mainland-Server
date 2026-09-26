const express = require('express');
const cors = require('cors');

const app = express();
const port = process.env.PORT || 8080;

app.use(cors());
app.use(express.json());

const events = [];

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', service: 'network-globe', uptime: process.uptime() });
});

app.get('/api/events', (_req, res) => {
  res.json(events.slice(-100));
});

app.post('/api/events', (req, res) => {
  const event = { ...req.body, timestamp: new Date().toISOString() };
  events.push(event);
  res.status(201).json(event);
});

app.listen(port, () => {
  console.log(`Network Globe listening on ${port}`);
});
