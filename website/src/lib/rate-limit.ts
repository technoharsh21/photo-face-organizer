const tracker = new Map<string, number[]>();

export function checkRateLimit(ip: string, limit = 5, windowMs = 60 * 1000): boolean {
  const now = Date.now();
  const timestamps = tracker.get(ip) || [];

  // Filter timestamps within window
  const validTimestamps = timestamps.filter((ts) => now - ts < windowMs);

  if (validTimestamps.length >= limit) {
    return false;
  }

  validTimestamps.push(now);
  tracker.set(ip, validTimestamps);
  return true;
}
