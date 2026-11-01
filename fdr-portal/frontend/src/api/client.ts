import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api

// ---- Auth ----
export const login = (email: string, password: string) =>
  api.post('/auth/login', { email, password }).then(r => r.data.data)

export const getMe = () =>
  api.get('/auth/me').then(r => r.data.data)

// ---- Institutions ----
export const getInstitutions = () => api.get('/institutions').then(r => r.data.data)
export const createInstitution = (d: any) => api.post('/institutions', d).then(r => r.data.data)
export const updateInstitution = (id: string, d: any) => api.patch(`/institutions/${id}`, d).then(r => r.data.data)

// ---- Banks ----
export const getBanks = () => api.get('/banks').then(r => r.data.data)
export const createBank = (d: any) => api.post('/banks', d).then(r => r.data.data)
export const updateBank = (id: string, d: any) => api.patch(`/banks/${id}`, d).then(r => r.data.data)

// ---- Regulatory Rules ----
export const getRegulatoryRules = (year?: string) =>
  api.get('/regulatory-rules', { params: { year } }).then(r => r.data.data)

// ---- Deposits ----
export const getDeposits = () => api.get('/deposits').then(r => r.data.data)
export const getDeposit = (id: string) => api.get(`/deposits/${id}`).then(r => r.data.data)
export const createDeposit = (d: any) => api.post('/deposits', d).then(r => r.data.data)
export const updateDeposit = (id: string, d: any) => api.patch(`/deposits/${id}`, d).then(r => r.data.data)

// ---- FDRs ----
export const getFDRs = (params?: any) => api.get('/fdrs', { params }).then(r => r.data.data)
export const getFDR = (id: string) => api.get(`/fdrs/${id}`).then(r => r.data.data)
export const createFDR = (d: any) => api.post('/fdrs', d).then(r => r.data.data)
export const updateFDR = (id: string, d: any) => api.patch(`/fdrs/${id}`, d).then(r => r.data.data)
export const transitionFDR = (id: string, to_status: string, note?: string) =>
  api.post(`/fdrs/${id}/transition`, { to_status, note }).then(r => r.data.data)
export const renewFDR = (id: string, d: any) => api.post(`/fdrs/${id}/renew`, d).then(r => r.data.data)

// ---- Documents ----
export const uploadDocument = (fdr_id: string, file: File) => {
  const fd = new FormData()
  fd.append('file', file)
  return api.post(`/documents/fdrs/${fdr_id}/document`, fd, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(r => r.data.data)
}
export const getDocumentOCR = (doc_id: string) => api.get(`/documents/${doc_id}/ocr`).then(r => r.data.data)
export const reviewOCRField = (field_id: string, reviewed_value: string) =>
  api.post(`/ocr-fields/${field_id}/review`, { reviewed_value }).then(r => r.data.data)
export const getReviewQueue = () => api.get('/review-queue').then(r => r.data.data)

// ---- Bank Verification ----
export const getVerification = (fdr_id: string) => api.get(`/fdrs/${fdr_id}/verification`).then(r => r.data.data)
export const submitVerification = (fdr_id: string, d: any) => api.post(`/fdrs/${fdr_id}/verification`, d).then(r => r.data.data)
export const decideVerification = (fdr_id: string, decision: string, remarks?: string) =>
  api.post(`/fdrs/${fdr_id}/verification/decide`, { decision, remarks }).then(r => r.data.data)

// ---- Discrepancies ----
export const getDiscrepancies = (params?: any) => api.get('/discrepancies', { params }).then(r => r.data.data)
export const resolveCase = (id: string, note: string) => api.post(`/discrepancies/${id}/resolve`, { note }).then(r => r.data.data)
export const waiveCase = (id: string, note: string) => api.post(`/discrepancies/${id}/waive`, { note }).then(r => r.data.data)
export const getRules = () => api.get('/rules').then(r => r.data.data)
export const updateRule = (id: string, d: any) => api.patch(`/rules/${id}`, d).then(r => r.data.data)

// ---- Alerts ----
export const getAlerts = (params?: any) => api.get('/alerts', { params }).then(r => r.data.data)
export const acknowledgeAlert = (id: string) => api.post(`/alerts/${id}/acknowledge`).then(r => r.data.data)

// ---- Renewals ----
export const getRenewals = () => api.get('/renewals').then(r => r.data.data)

// ---- Releases ----
export const getReleases = () => api.get('/releases').then(r => r.data.data)
export const getRelease = (id: string) => api.get(`/releases/${id}`).then(r => r.data.data)
export const createRelease = (d: any) => api.post('/releases', d).then(r => r.data.data)
export const updateReleaseDoc = (id: string, d: any) => api.post(`/releases/${id}/documents`, d).then(r => r.data.data)
export const updateClearance = (id: string, cell: string, d: any) =>
  api.post(`/releases/${id}/clearances/${cell}`, d).then(r => r.data.data)
export const decideStep = (id: string, step_no: number, d: any) =>
  api.post(`/releases/${id}/steps/${step_no}/decide`, d).then(r => r.data.data)
export const recordNOC = (id: string, d: any) => api.post(`/releases/${id}/noc`, d).then(r => r.data.data)
export const closeRelease = (id: string) => api.post(`/releases/${id}/close`).then(r => r.data.data)

// ---- Dashboard ----
export const getDashboardSummary = () => api.get('/dashboard/summary').then(r => r.data.data)
export const getMaturityCalendar = (days?: number) =>
  api.get('/dashboard/maturity-calendar', { params: { days } }).then(r => r.data.data)
export const getCompliance = () => api.get('/dashboard/compliance').then(r => r.data.data)

// ---- Reports ----
export const downloadReport = (path: string, params?: any) => {
  return api.get(`/reports/${path}`, { params, responseType: 'blob' }).then(r => {
    const url = URL.createObjectURL(r.data)
    const a = document.createElement('a')
    a.href = url
    a.download = r.headers['content-disposition']?.split('filename=')[1] || 'report'
    a.click()
    URL.revokeObjectURL(url)
  })
}

// ---- Audit ----
export const getAuditLog = (params?: any) => api.get('/audit', { params }).then(r => r.data.data)
export const verifyAuditChain = () => api.get('/audit/verify').then(r => r.data.data)
export const simulateTamper = () => api.post('/audit/tamper-simulate').then(r => r.data.data)
export const restoreTamper = (entry_id: string, original_action: string) =>
  api.post('/audit/tamper-restore', null, { params: { entry_id, original_action } }).then(r => r.data.data)

// ---- Admin ----
export const setDemoClock = (d: any) => api.post('/admin/demo-clock', d).then(r => r.data.data)
export const runScheduler = () => api.post('/admin/run-scheduler').then(r => r.data.data)
export const getUsers = () => api.get('/admin/users').then(r => r.data.data)
export const createUser = (d: any) => api.post('/admin/users', d).then(r => r.data.data)
export const getSystemSettings = () => api.get('/admin/settings').then(r => r.data.data)
