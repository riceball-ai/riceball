// Import highlight.js styles
import 'highlight.js/styles/github.css'

export default defineNuxtPlugin(() => {
  // Client initialization logic
  if (process.client) {
    // Add custom styles to override highlight.js background color
    const style = document.createElement('style')
    style.textContent = `
      /* Override highlight.js background color */
      .hljs {
        background: transparent !important;
        color: inherit !important;
      }
      
      /* Adjust code color in dark theme */
      .dark .hljs {
        color: #e1e4e8 !important;
      }
    `
    document.head.appendChild(style)
  }
})
