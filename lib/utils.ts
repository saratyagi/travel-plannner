export function extractDestination(text: string): string | null {
  // "from X to Y" → Y
  let m = text.match(/\bfrom\s+[\w\s]+?\s+to\s+([A-Z][A-Za-z\s]+?)(?=\s+for\b|\s+in\b|\s+on\b|\s+from\b|\s+,|,|\.|$)/i);
  if (m?.[1]?.trim()) return m[1].trim();

  // "trip/travel/fly/going/head to Y"
  m = text.match(/\b(?:trip|travel|fly(?:ing)?|going|head(?:ing)?|visit(?:ing)?|explore)\s+(?:from\s+\S+\s+)?to\s+([A-Z][A-Za-z\s]+?)(?=\s+for\b|\s+in\b|\s+on\b|\s+,|,|\.|$)/i);
  if (m?.[1]?.trim()) return m[1].trim();

  // plain "to Y" with capital letter
  m = text.match(/\bto\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)(?=\s+for\b|\s+in\b|\s+on\b|\s+,|,|\s+\d|\.| |$)/);
  if (m?.[1]?.trim()) return m[1].trim();

  // "X to Y" at start (e.g. "Dubai to Bali")
  m = text.match(/^([A-Za-z]+(?:\s[A-Za-z]+)?)\s+to\s+([A-Za-z]+(?:\s[A-Za-z]+)?)/i);
  if (m?.[2]?.trim()) return m[2].trim();

  return null;
}
