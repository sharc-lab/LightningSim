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
