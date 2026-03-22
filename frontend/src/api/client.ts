import axios from 'axios'
import { supabase } from '@/lib/supabase'

const client = axios.create({
  baseURL: (import.meta as unknown as { env: Record<string, string> }).env.VITE_API_URL ?? 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

client.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession()
  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`
  }
  return config
})

export default client
