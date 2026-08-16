export type DeploymentMode = 'standalone' | 'hub'

export interface RuntimeConfig {
  mode: DeploymentMode
  apiBaseUrl: string
  platformCoreUrl: string
  productName: string
}

const DEFAULTS: RuntimeConfig = {
  mode: 'standalone',
  apiBaseUrl: '/api/v1',
  platformCoreUrl: '',
  productName: 'OpenVizion',
}

let cached: RuntimeConfig | null = null

export async function loadRuntimeConfig(url = '/config.json'): Promise<RuntimeConfig> {
  if (cached) {
    return cached
  }
  try {
    const response = await fetch(url, { cache: 'no-store' })
    if (!response.ok) {
      cached = { ...DEFAULTS }
      return cached
    }
    const raw = (await response.json()) as Partial<RuntimeConfig> & {
      MODE?: string
      API_BASE_URL?: string
      PLATFORM_CORE_URL?: string
      PRODUCT_NAME?: string
    }
    cached = {
      mode: (raw.mode ?? raw.MODE ?? DEFAULTS.mode) === 'hub' ? 'hub' : 'standalone',
      apiBaseUrl: raw.apiBaseUrl ?? raw.API_BASE_URL ?? DEFAULTS.apiBaseUrl,
      platformCoreUrl: raw.platformCoreUrl ?? raw.PLATFORM_CORE_URL ?? DEFAULTS.platformCoreUrl,
      productName: raw.productName ?? raw.PRODUCT_NAME ?? DEFAULTS.productName,
    }
    return cached
  } catch {
    cached = { ...DEFAULTS }
    return cached
  }
}

export function getRuntimeConfig(): RuntimeConfig {
  return cached ?? { ...DEFAULTS }
}

export function resetRuntimeConfigForTests(): void {
  cached = null
}
