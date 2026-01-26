import fs from 'fs';
import path from 'path';

/**
 * Logger utility for consistent logging across the application
 */
export class Logger {
  constructor(module = 'App', logDir = './logs') {
    this.module = module;
    this.logDir = logDir;
    this.logFile = path.join(logDir, `sentiment-synthesizer_${new Date().toISOString().split('T')[0]}.log`);
    this.ensureLogDir();
  }

  ensureLogDir() {
    if (!fs.existsSync(this.logDir)) {
      fs.mkdirSync(this.logDir, { recursive: true });
    }
  }

  /**
   * Format log message
   */
  formatMessage(level, message, data = null) {
    const timestamp = new Date().toISOString();
    const dataStr = data ? ` | ${JSON.stringify(data)}` : '';
    return `[${timestamp}] [${level.toUpperCase()}] [${this.module}] ${message}${dataStr}`;
  }

  /**
   * Write to log file
   */
  writeToFile(message) {
    try {
      fs.appendFileSync(this.logFile, message + '\n');
    } catch (error) {
      console.error('Error writing to log file:', error);
    }
  }

  /**
   * Info level logging
   */
  info(message, data = null) {
    const formatted = this.formatMessage('info', message, data);
    console.log(formatted);
    this.writeToFile(formatted);
  }

  /**
   * Debug level logging
   */
  debug(message, data = null) {
    const formatted = this.formatMessage('debug', message, data);
    console.log(formatted);
    this.writeToFile(formatted);
  }

  /**
   * Warning level logging
   */
  warn(message, data = null) {
    const formatted = this.formatMessage('warn', message, data);
    console.warn(formatted);
    this.writeToFile(formatted);
  }

  /**
   * Error level logging
   */
  error(message, data = null) {
    const formatted = this.formatMessage('error', message, data);
    console.error(formatted);
    this.writeToFile(formatted);
  }

  /**
   * Success level logging
   */
  success(message, data = null) {
    const formatted = this.formatMessage('success', message, data);
    console.log(`✅ ${formatted}`);
    this.writeToFile(formatted);
  }

  /**
   * Performance timing
   */
  startTimer(label) {
    console.time(`⏱️  ${label}`);
  }

  /**
   * End performance timing
   */
  endTimer(label) {
    console.timeEnd(`⏱️  ${label}`);
  }
}

// Create a default logger instance
export const defaultLogger = new Logger('SentimentSynthesizer');
