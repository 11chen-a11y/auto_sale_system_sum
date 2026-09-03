// 导出工具：把后端返回的 Blob（CSV 等）触发为浏览器下载
export function saveBlob(res, fallbackName = 'export.csv') {
  const disposition = res.headers?.['content-disposition'] || ''
  const match = disposition.match(/filename="?([^";]+)"?/)
  const filename = match ? match[1] : fallbackName
  const url = URL.createObjectURL(new Blob([res.data], { type: 'text/csv;charset=utf-8' }))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
