export function searchNodes(nodes, query, limit = 8) {
  const q = query.trim().toLowerCase()
  if (!q) return []
  const rank = (n) => { const s = n.name.toLowerCase(); return s.startsWith(q) ? 0 : s.includes(q) ? 1 : -1 }
  return nodes.map((n) => [rank(n), n]).filter(([r]) => r >= 0)
    .sort((a, b) => a[0] - b[0] || a[1].name.localeCompare(b[1].name))
    .slice(0, limit).map(([, n]) => n)
}
