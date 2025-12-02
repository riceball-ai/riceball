import { toast } from 'vue-sonner'

export interface NotificationAction {
  label: string
  onClick: () => void
}

export interface NotificationOptions {
  duration?: number
  action?: NotificationAction
}

export function useNotifications() {
  const showSuccess = (message: string, options?: NotificationOptions) => {
    toast.success(message, {
      duration: options?.duration,
      action: options?.action,
    })
  }

  const showError = (message: string, options?: NotificationOptions) => {
    toast.error(message, {
      duration: options?.duration,
      action: options?.action,
    })
  }

  const showInfo = (message: string, options?: NotificationOptions) => {
    toast.info(message, {
      duration: options?.duration,
      action: options?.action,
    })
  }

  const showWarning = (message: string, options?: NotificationOptions) => {
    toast.warning(message, {
      duration: options?.duration,
      action: options?.action,
    })
  }

  return {
    showSuccess,
    showError,
    showInfo,
    showWarning
  }
}
