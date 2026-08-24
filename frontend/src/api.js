async function handle(resp) {
  if (!resp.ok) {
    let detail = `${resp.status} ${resp.statusText}`
    try {
      const data = await resp.json()
      if (data.detail) detail = data.detail
    } catch { /* non-JSON error body */ }
    throw new Error(detail)
  }
  return resp.json()
}

export const get = (url) => fetch(url).then(handle)

export const postJSON = (url, body) =>
  fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(handle)

export const postForm = (url, formData) =>
  fetch(url, { method: 'POST', body: formData }).then(handle)

export const del = (url) => fetch(url, { method: 'DELETE' }).then(handle)
