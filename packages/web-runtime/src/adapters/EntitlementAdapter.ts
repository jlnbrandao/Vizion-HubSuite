export interface EntitlementAdapter {
  has(capability: string): boolean
  services(): string[]
}

export function createEntitlementAdapter(services: string[], capabilities: string[]): EntitlementAdapter {
  const serviceSet = new Set(services)
  const caps = new Set(capabilities)
  return {
    has(capability: string) {
      return caps.has(capability) || serviceSet.has(capability)
    },
    services() {
      return [...serviceSet]
    },
  }
}
