/**
 * Read CSS variable–based design tokens at runtime for Recharts axes/labels.
 * Call inside a render function so it reads values after dark/light class is applied.
 */
export function getChartColors() {
  const style = getComputedStyle(document.documentElement)
  const get = (v: string) => `hsl(${style.getPropertyValue(v).trim()})`
  return {
    foreground: get('--foreground'),
    mutedForeground: get('--muted-foreground'),
    border: get('--border'),
    background: get('--background'),
    primary: get('--primary'),
    card: get('--card'),
  }
}
