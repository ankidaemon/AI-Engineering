/**
 * Utility Functions
 * Common helper functions used across modules
 */

/**
 * Sleep for specified milliseconds
 */
export function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Retry function with exponential backoff
 */
export async function retry(fn, options = {}) {
  const {
    maxAttempts = 3,
    delay = 1000,
    backoff = 2,
    onError = null
  } = options;

  let lastError;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      
      if (onError) {
        onError(error, attempt, maxAttempts);
      }

      if (attempt < maxAttempts) {
        const waitTime = delay * Math.pow(backoff, attempt - 1);
        await sleep(waitTime);
      }
    }
  }

  throw lastError;
}

/**
 * Batch array into smaller chunks
 */
export function batch(array, size) {
  const batches = [];
  
  for (let i = 0; i < array.length; i += size) {
    batches.push(array.slice(i, i + size));
  }
  
  return batches;
}

/**
 * Calculate percentile
 */
export function percentile(array, p) {
  const sorted = [...array].sort((a, b) => a - b);
  const index = Math.ceil(sorted.length * p / 100) - 1;
  return sorted[Math.max(0, index)];
}

/**
 * Calculate median
 */
export function median(array) {
  return percentile(array, 50);
}

/**
 * Calculate mean
 */
export function mean(array) {
  return array.reduce((a, b) => a + b, 0) / array.length;
}

/**
 * Calculate standard deviation
 */
export function stdDev(array) {
  const avg = mean(array);
  const squareDiffs = array.map(val => Math.pow(val - avg, 2));
  const variance = mean(squareDiffs);
  return Math.sqrt(variance);
}

/**
 * Normalize values to [0, 1]
 */
export function normalize(array) {
  const min = Math.min(...array);
  const max = Math.max(...array);
  const range = max - min || 1;
  
  return array.map(val => (val - min) / range);
}

/**
 * Format number with precision
 */
export function formatNumber(num, precision = 2) {
  return parseFloat(num.toFixed(precision));
}

/**
 * Format percentage
 */
export function formatPercentage(num, precision = 2) {
  return `${formatNumber(num * 100, precision)}%`;
}

/**
 * Capitalize first letter
 */
export function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Remove duplicates from array
 */
export function unique(array) {
  return [...new Set(array)];
}

/**
 * Group array by key
 */
export function groupBy(array, key) {
  return array.reduce((grouped, item) => {
    const group = item[key];
    if (!grouped[group]) {
      grouped[group] = [];
    }
    grouped[group].push(item);
    return grouped;
  }, {});
}

/**
 * Sort object by values
 */
export function sortByValue(obj, ascending = false) {
  return Object.entries(obj)
    .sort((a, b) => ascending ? a[1] - b[1] : b[1] - a[1])
    .reduce((sorted, [key, value]) => {
      sorted[key] = value;
      return sorted;
    }, {});
}

/**
 * Deep clone object
 */
export function deepClone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

/**
 * Merge objects
 */
export function merge(target, source) {
  const result = { ...target };
  
  Object.keys(source).forEach(key => {
    if (typeof source[key] === 'object' && source[key] !== null) {
      result[key] = merge(result[key] || {}, source[key]);
    } else {
      result[key] = source[key];
    }
  });
  
  return result;
}

/**
 * Simple template string replacement
 */
export function template(str, data) {
  return str.replace(/{{(\w+)}}/g, (match, key) => data[key] || match);
}

/**
 * Validate email
 */
export function isValidEmail(email) {
  const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return regex.test(email);
}

/**
 * Generate UUID
 */
export function generateId() {
  return `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Measure execution time
 */
export async function measureTime(fn, label = 'Execution') {
  const start = performance.now();
  const result = await fn();
  const end = performance.now();
  const duration = formatNumber(end - start, 2);
  
  console.log(`⏱️  ${label}: ${duration}ms`);
  
  return { result, duration };
}

/**
 * Parse JSON safely
 */
export function parseJSON(str, defaultValue = null) {
  try {
    return JSON.parse(str);
  } catch {
    return defaultValue;
  }
}

/**
 * Truncate string
 */
export function truncate(str, maxLength = 100, suffix = '...') {
  if (str.length <= maxLength) return str;
  return str.slice(0, maxLength) + suffix;
}

/**
 * Get nested property safely
 */
export function getNestedProperty(obj, path, defaultValue = undefined) {
  const keys = path.split('.');
  let value = obj;

  for (const key of keys) {
    value = value?.[key];
    if (value === undefined) {
      return defaultValue;
    }
  }

  return value;
}

/**
 * Check if object is empty
 */
export function isEmpty(obj) {
  return Object.keys(obj).length === 0;
}

export default {
  sleep,
  retry,
  batch,
  percentile,
  median,
  mean,
  stdDev,
  normalize,
  formatNumber,
  formatPercentage,
  capitalize,
  unique,
  groupBy,
  sortByValue,
  deepClone,
  merge,
  template,
  isValidEmail,
  generateId,
  measureTime,
  parseJSON,
  truncate,
  getNestedProperty,
  isEmpty
};
