import { defineStore } from 'pinia'
import { FetchError } from 'ofetch'
import type { User } from '~/types/api'

export const useUserStore = defineStore('user', {
  state: () => ({
    user: null as User | null,
    loading: false,
    verificationRequired: false,
  }),

  getters: {
    currentUser: (state) => state.user,
  },

  actions: {
    async fetchUser(): Promise<boolean> {
      this.loading = true
      try {
        const { $api } = useNuxtApp()
        const data = await $api<User>('/v1/users/me')
        
        this.user = data
        return true
      } catch (error) {
        this.user = null

        if (!(error instanceof FetchError)) throw error;

        return false
      } finally {
        this.loading = false
      }
    },

    async logout() {
      try {
        const { $api } = useNuxtApp()
        await $api('/v1/auth/logout', {
          method: 'POST'
        })
      } catch (error) {
      } finally {
        this.user = null
      }
    },

    clearUser() {
      this.user = null
    }
  }
})
