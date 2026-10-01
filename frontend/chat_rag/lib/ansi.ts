// Converte os códigos de cor de terminal (ANSI/SGR) que o MASPY usa em cores CSS,
// para o console do site ficar com as mesmas cores do prompt de comando.

const ANSI = /\x1b\[([0-9;]*)m/g

// 16 cores básicas (paleta do terminal escuro do VS Code): 30–37 / 90–97
const BASIC = [
  '#000000', '#cd3131', '#0dbc79', '#e5e510', '#2472c8', '#bc3fbc', '#11a8cd', '#e5e5e5',
  '#666666', '#f14c4c', '#23d18b', '#f5f543', '#3b8eea', '#d670d6', '#29b8db', '#ffffff',
]

/** Cor da paleta xterm de 256 cores (códigos 38;5;N). */
function xterm256(n: number): string {
  if (n < 16) return BASIC[n]
  if (n >= 232) {
    const g = 8 + 10 * (n - 232)
    return `rgb(${g}, ${g}, ${g})`
  }
  const i = n - 16
  const level = (v: number) => (v === 0 ? 0 : 55 + 40 * v)
  return `rgb(${level(Math.floor(i / 36))}, ${level(Math.floor((i % 36) / 6))}, ${level(i % 6)})`
}

/** Remove os códigos de cor, deixando só o texto. */
export function stripAnsi(text: string): string {
  return text.replace(ANSI, '')
}

/** Primeira cor de texto definida na linha (o MASPY pinta a linha inteira com uma cor só). */
export function lineColor(text: string): string | undefined {
  for (const m of text.matchAll(ANSI)) {
    const codes = m[1].split(';').map(Number)
    for (let i = 0; i < codes.length; i++) {
      const c = codes[i]
      if (c >= 30 && c <= 37) return BASIC[c - 30]
      if (c >= 90 && c <= 97) return BASIC[c - 90 + 8]
      if (c === 38 && codes[i + 1] === 5 && codes[i + 2] !== undefined) return xterm256(codes[i + 2])
      if (c === 38 && codes[i + 1] === 2 && codes.length >= i + 5) {
        return `rgb(${codes[i + 2]}, ${codes[i + 3]}, ${codes[i + 4]})`
      }
    }
  }
  return undefined
}
