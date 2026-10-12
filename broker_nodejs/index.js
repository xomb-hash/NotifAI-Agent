try {
  require('dotenv').config();
} catch (err) {
  // Environment variables are provided by Docker Compose / OS environment
}

const { startBroker } = require('./wa_listener');

console.log('Starting NotifAI WhatsApp Web Broker service...');

startBroker().catch((err) => {
  console.error('Fatal error in NotifAI WhatsApp Broker service:', err);
  process.exit(1);
});
