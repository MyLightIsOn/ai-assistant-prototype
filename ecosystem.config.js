// PM2 Configuration for AI Assistant
const path = require('path');

module.exports = {
  apps: [
    {
      name: 'ai-assistant-web',
      script: 'npm',
      args: 'start',
      cwd: path.join(__dirname, 'frontend'),
      env: {
        NODE_ENV: 'production',
        PORT: 3000
      },
      error_file: path.join(__dirname, 'logs/web-error.log'),
      out_file: path.join(__dirname, 'logs/web-out.log'),
      time: true
    },
    {
      name: 'ai-assistant-backend',
      script: 'python',
      args: 'main.py',
      cwd: path.join(__dirname, 'backend'),
      interpreter: path.join(__dirname, 'backend/venv/bin/python'),
      env: {
        PYTHONUNBUFFERED: '1'
      },
      error_file: path.join(__dirname, 'logs/backend-error.log'),
      out_file: path.join(__dirname, 'logs/backend-out.log'),
      time: true
    },
    {
      name: 'ai-assistant-scheduler',
      script: 'python',
      args: 'scheduler.py',
      cwd: path.join(__dirname, 'backend'),
      interpreter: path.join(__dirname, 'backend/venv/bin/python'),
      env: {
        PYTHONUNBUFFERED: '1'
      },
      error_file: path.join(__dirname, 'logs/scheduler-error.log'),
      out_file: path.join(__dirname, 'logs/scheduler-out.log'),
      time: true
    }
  ]
};
