import { apiAdminGet, apiAdminPost, apiAdminPut, apiAdminDelete } from './base'

const BASE_URL = '/api/system/roleCard'

export const getRoleCards = async () => {
  return apiAdminGet(BASE_URL)
}

export const getRoleCard = async (name) => {
  return apiAdminGet(`${BASE_URL}/${encodeURIComponent(name)}`)
}

export const createRoleCard = async (data) => {
  return apiAdminPost(BASE_URL, data)
}

export const updateRoleCard = async (name, data) => {
  return apiAdminPut(`${BASE_URL}/${encodeURIComponent(name)}`, data)
}

export const deleteRoleCard = async (name) => {
  return apiAdminDelete(`${BASE_URL}/${encodeURIComponent(name)}`)
}

export const roleCardApi = {
  getRoleCards,
  getRoleCard,
  createRoleCard,
  updateRoleCard,
  deleteRoleCard
}

export default roleCardApi
