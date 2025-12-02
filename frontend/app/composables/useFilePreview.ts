interface BasePreviewPayload {
  title?: string
  description?: string
}

export interface SvgPreviewPayload extends BasePreviewPayload {
  type: 'svg'
  content: string
}

export type FilePreviewPayload = SvgPreviewPayload

type FilePreviewType = FilePreviewPayload['type'] | null

interface FilePreviewState {
  open: boolean
  type: FilePreviewType
  title?: string
  description?: string
  content: string
}

const initialState: FilePreviewState = {
  open: false,
  type: null,
  title: undefined,
  description: undefined,
  content: ''
}

const useFilePreviewState = () =>
  useState<FilePreviewState>('file-preview-state', () => ({ ...initialState }))

export const useFilePreview = () => {
  const previewState = useFilePreviewState()

  const openPreview = (payload: FilePreviewPayload) => {
    previewState.value = {
      open: true,
      type: payload.type,
      title: payload.title,
      description: payload.description,
      content: payload.content
    }
  }

  const closePreview = () => {
    previewState.value = {
      ...initialState
    }
  }

  return {
    previewState,
    openPreview,
    closePreview
  }
}
