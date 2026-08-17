export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  user_id: string | null
  email: string
  full_name: string
  mfa_required?: boolean
  mfa_token?: string | null
}

export interface DashboardWidget {
  id: string
  title: string
  widget_type: string
  data: Record<string, unknown>
}

export interface DashboardResponse {
  user_id: string
  email: string
  full_name: string
  tenant_id?: string | null
  tenant_slug?: string
  tenant_name?: string
  role_names: string[]
  permissions: string[]
  widgets: DashboardWidget[]
}

/** GET /navigation — menu already filtered by entitlement + RBAC. */
export interface NavigationItemResponse {
  id: string
  label: string
  icon: string
  route: string
  group: string
  service?: string | null
  permission?: string | null
  quick: boolean
}

export interface NavigationResponse {
  home_route: string
  services: string[]
  items: NavigationItemResponse[]
}

/** Service catalog — what the Hub offers and what a tenant has contracted. */
export interface ServiceResponse {
  slug: string
  namespace: string
  name: string
  description: string
  version: string
  is_core: boolean
  is_active: boolean
}

export interface TenantServiceResponse extends ServiceResponse {
  status: string | null
  plan: string | null
  entitled: boolean
  quotas: Record<string, unknown>
  expires_at?: string | null
}

export interface SetTenantServicePayload {
  status: string
  plan?: string | null
  quotas?: Record<string, unknown> | null
  expires_at?: string | null
}

/** Metering — what a tenant consumed per service, metric and period. */
export interface UsageRecordResponse {
  service: string
  metric: string
  granularity: 'day' | 'month'
  period_start: string
  quantity: number
}

export interface UsageReportResponse {
  tenant_id: string
  since: string
  until: string
  totals_by_service: Record<string, number>
  records: UsageRecordResponse[]
}

export interface UsageQuery {
  since?: string
  until?: string
  service?: string
  granularity?: 'day' | 'month'
}

/** GET /auth/me — identity and effective access (no longer carried in the JWT). */
export interface MeResponse {
  id: string
  email: string
  full_name: string
  tenant_id: string
  tenant_slug: string
  tenant_name?: string
  role_names: string[]
  permissions: string[]
  services: string[]
}

export interface AuthUser {
  id: string
  email: string
  fullName: string
  tenantId?: string | null
  tenantSlug?: string
  tenantName?: string
  roleNames: string[]
  permissions: string[]
  /** Services the tenant is entitled to; gates whole frontend modules. */
  services: string[]
}

export interface UserResponse {
  id: string
  email: string
  username: string
  full_name: string
  role_ids: string[]
  is_active: boolean
  created_at: string | null
  updated_at: string | null
}

export interface CreateUserPayload {
  email: string
  username: string
  full_name: string
  password: string
  role_ids: string[]
}

export interface UpdateUserPayload {
  username: string
  full_name: string
  is_active: boolean
}

export interface ChangePasswordPayload {
  new_password: string
}

export interface RoleResponse {
  id: string
  name: string
  description: string
  permission_ids: string[]
  is_active: boolean
  created_at: string | null
  updated_at: string | null
}

export interface CreateRolePayload {
  name: string
  description: string
}

export interface UpdateRolePayload {
  description: string
  is_active: boolean
}

export interface PermissionResponse {
  id: string
  code: string
  legacy_code: string | null
  service: string | null
  resource: string
  action: string
  name: string
  description: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface PermissionCatalogEntryResponse {
  code: string
  legacy_code: string
  service: string
  resource: string
  action: string
  name: string
  description: string
}

export interface PermissionBundleResponse {
  id: string
  slug: string
  service: string
  name: string
  description: string
  is_active: boolean
  permission_ids: string[]
  permission_codes: string[]
}

export interface UpsertPermissionBundlePayload {
  slug: string
  service: string
  name: string
  description: string
  permission_ids: string[]
}

export interface CreatePermissionPayload {
  code: string
  name: string
  description: string
}

export interface UpdatePermissionPayload {
  name: string
  description: string
  is_active: boolean
}

export interface IdResponse {
  id: string
}

export interface TenantAdminResponse {
  id: string
  username: string
  email: string
  full_name: string
}

export interface TenantResponse {
  id: string
  slug: string
  name: string
  is_active: boolean
  admin: TenantAdminResponse | null
}

export interface CreateTenantPayload {
  slug: string
  name: string
  admin_username: string
  admin_email: string
  admin_full_name: string
  admin_password: string
}


export interface RenameTenantPayload {
  name: string
}

export interface BillingChargeLine {
  kind: 'user' | 'service' | 'discount' | string
  label: string
  quantity: number
  unit_amount: string | number
  amount: string | number
  ref?: string | null
  included?: boolean
  enabled?: boolean
}

export interface BillingOverviewResponse {
  generated_at: string
  period_start: string
  period_end: string
  payment_due: string
  days_elapsed: number
  prepayments: string | number
  discount: string | number
  subtotal: string | number
  total: string | number
  users: BillingChargeLine[]
  services: BillingChargeLine[]
  promo_code?: string | null
}

export interface BillingInvoiceLine {
  kind: string
  label: string
  quantity: number
  unit_amount: string | number
  amount: string | number
  ref?: string | null
}

export interface BillingInvoiceResponse {
  id: string
  period_start: string
  period_end: string
  status: string
  subtotal: string | number
  discount: string | number
  total: string | number
  description: string
  invoice_url?: string | null
  pix_payload?: string | null
  created_at: string
  lines: BillingInvoiceLine[]
}

export interface BillingPaymentMethodResponse {
  id: string
  billing_type: string
  brand: string
  last4: string
  holder_name: string
  is_primary: boolean
  credit_card_token?: string | null
}

export interface CreateBillingPaymentMethodPayload {
  billing_type?: string
  credit_card_token?: string
  brand?: string
  last4?: string
  holder_name?: string
  is_primary?: boolean
  card_number?: string
  expiry_month?: string
  expiry_year?: string
  ccv?: string
}

export interface BillingSettingsResponse {
  legal_name: string
  email: string
  cpf_cnpj: string
  postal_code: string
  address: string
  address_number: string
  complement: string
  province: string
  city: string
  state: string
  country: string
  cycle_close_day: number
  alert_enabled: boolean
  promo_code?: string | null
  asaas_linked: boolean
  contracted_services: BillingChargeLine[]
}

export interface UpdateBillingSettingsPayload {
  legal_name?: string
  email?: string
  cpf_cnpj?: string
  postal_code?: string
  address?: string
  address_number?: string
  complement?: string
  province?: string
  city?: string
  state?: string
  country?: string
  cycle_close_day?: number
  alert_enabled?: boolean
}

export interface CreateBillingPaymentPayload {
  billing_type?: string
  payment_method_id?: string
  amount?: number
}

export interface CreateBillingPaymentResponse {
  invoice: BillingInvoiceResponse
  invoice_url?: string | null
  pix_payload?: string | null
}

export interface ProductBindingResponse {
  tenant_id: string
  tenant_slug?: string
  tenant_name?: string
  product_instance_id: string
  service_slug: string
  status: string
}

export interface ProductInstanceResponse {
  id: string
  slug: string
  name: string
  base_url: string
  ui_url: string | null
  status: string
  version: string
  client_id: string
  last_heartbeat_at: string | null
  environment: string
  host: string
  api_port: number | null
  ui_host: string | null
  ui_port: number | null
  scheme: string
  notes: string
  bindings: ProductBindingResponse[]
}

export interface HubLocationResponse {
  kind: string
  name: string
  environment: string
  host: string
  api_port: number
  ui_port: number
  api_url: string
  ui_url: string
  services: string[]
  notes: string
  runtime: string
}

export interface ProductSlugOption {
  slug: string
  name: string
}

export interface ProductTopologyResponse {
  hub: HubLocationResponse
  instances: ProductInstanceResponse[]
  product_options?: ProductSlugOption[]
}

export type ProductSlug = 'tracking' | 'iot' | 'snmp' | 'gis' | 'lanstar'

export interface CreateProductInstancePayload {
  slug: ProductSlug
  name: string
  client_id: string
  client_secret: string
  environment: string
  host: string
  api_port: number | null
  ui_host?: string | null
  ui_port?: number | null
  scheme: string
  base_url?: string
  ui_url?: string | null
  notes?: string
}

export interface UpdateProductInstancePayload {
  name?: string
  environment?: string
  host?: string
  api_port?: number | null
  ui_host?: string | null
  ui_port?: number | null
  scheme?: string
  base_url?: string
  ui_url?: string | null
  notes?: string
  status?: string
}


