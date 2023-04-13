export const formatDuration = (seconds: number, fractionDigits?: number): string => {
  if (seconds < 0) {
    return `-${formatDuration(-seconds, fractionDigits)}`;
  }

  const minutes = Math.trunc(seconds / 60);
  const secondsPart = `${(seconds % 60).toFixed(fractionDigits)}s`;
  if (minutes === 0) {
    return secondsPart;
  }

  const hours = Math.trunc(minutes / 60);
  const minutesPart = `${minutes % 60}m`;
  if (hours === 0) {
    return `${minutesPart} ${secondsPart}`;
  }

  const days = Math.trunc(hours / 24);
  const hoursPart = `${hours % 24}h`;
  if (days === 0) {
    return `${hoursPart} ${minutesPart} ${secondsPart}`;
  }

  const daysPart = `${days}d`;
  return `${daysPart} ${hoursPart} ${minutesPart} ${secondsPart}`;
};

export const formatTimeRemaining = (elapsed: number, progress: number): string => {
  const seconds = (elapsed / progress) - elapsed;
  if (seconds < 5) {
    return "a few seconds";
  }

  const minutes = Math.trunc(seconds / 60);
  if (minutes === 0) {
    const secondsTrunc = Math.trunc(seconds);
    return `${secondsTrunc}s`;
  }

  if (minutes < 10) {
    const secondsInTens = Math.trunc((seconds % 60) / 10) * 10;
    return `${minutes}m ${secondsInTens}s`;
  }

  const hours = Math.trunc(minutes / 60);
  const minutesPart = `${minutes % 60}m`;
  if (hours === 0) {
    return minutesPart;
  }

  const days = Math.trunc(hours / 24);
  const hoursPart = `${hours % 24}h`;
  if (days === 0) {
    return `${hoursPart} ${minutesPart}`;
  }

  const daysPart = `${days}d`;
  return `${daysPart} ${hoursPart}`;
};
