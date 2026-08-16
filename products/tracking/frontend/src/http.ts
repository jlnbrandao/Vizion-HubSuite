import axios from 'axios'
import { loadRuntimeConfig } from '@openvizion/web-runtime'

let memoryToken: string | null = null

export const tokenStorage = {
  get(): string | null {
    return memoryToken
  },
  set(token: string) {
    memoryToken = token
  },
  clear() {
    memoryToken = null
  },
}

export async function createHttp() {
  const config = await loadRuntimeConfig()
  const client = axios.create({
    baseURL: config.apiBaseUrl,
    headers: { 'Content-Type': 'application/json' },
  })
  client.interceptors.request.use((req) => {
    const token = tokenStorage.get()
    if (token) {
      req.headers.Authorization = `Bearer ${token}`
    }
    return req
  })
  return {
    async post<T>(path: string, body?: unknown): Promise<T> {
      const { data } = await client.post<T>(path, body)
      return data
    },
    async get<T>(path: string, token?: string): Promise<T> {
      const { data } = await client.get<T>(path, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      })
      return data
    },
    async delete(path: string) {
      await client.delete(path)
    },
    raw: client,
  }
}
