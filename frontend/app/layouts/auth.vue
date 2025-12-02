<script setup lang="ts">
const { t } = useI18n()
const runtimeConfig = useRuntimeConfig()
const typewriterText = ref('')
const fullText = t('common.slogan')

onMounted(() => {
  let index = 0
  const typeInterval = setInterval(() => {
    if (index < fullText.length) {
      typewriterText.value += fullText.charAt(index)
      index++
    } else {
      clearInterval(typeInterval)
    }
  }, 150)
})
</script>

<template>
  <div class="grid min-h-svh lg:grid-cols-2">
    <div class="flex flex-col gap-4 p-6 md:p-10">
      <div class="flex justify-center gap-2 md:justify-start">
        <div class="flex items-center gap-2 font-medium">
          <div class="flex size-10 items-center justify-center rounded-md">
             <img src="/logo.png" alt="Logo"/>
          </div>
          <span class="font-bold">{{ runtimeConfig.public.appName }}</span>
        </div>
      </div>
      <div class="flex flex-1 items-center justify-center">
        <div class="w-full max-w-xs">
          <slot />
        </div>
      </div>
    </div>
    <div class="relative hidden bg-gradient-to-br from-slate-900 via-slate-800 to-gray-900 lg:block lg:flex lg:flex-col overflow-hidden">
      <div class="absolute inset-0 bg-grid-pattern opacity-20"></div>
      <div class="absolute inset-0">
        <div class="floating-orb orb-1"></div>
        <div class="floating-orb orb-2"></div>
        <div class="floating-orb orb-3"></div>
      </div>
      
      <div class="flex-1 flex items-center justify-center relative z-10">
        <h1 class="text-3xl font-bold text-center text-white typewriter drop-shadow-lg">
          {{ typewriterText }}
          <span class="typewriter-cursor">|</span>
        </h1>
      </div>
  
    </div>
  </div>
</template>

<style scoped>
.typewriter-cursor {
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 50% {
    opacity: 1;
  }
  51%, 100% {
    opacity: 0;
  }
}

.bg-grid-pattern {
  background-image: 
    linear-gradient(rgba(255, 255, 255, 0.1) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.1) 1px, transparent 1px);
  background-size: 50px 50px;
}

.floating-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  animation: float 3s ease-in-out infinite;
}

.orb-1 {
  width: 200px;
  height: 200px;
  background: linear-gradient(45deg, #718096 0%, #4a5568 100%);
  top: 20%;
  right: 10%;
  animation-delay: 0s;
}

.orb-2 {
  width: 150px;
  height: 150px;
  background: linear-gradient(45deg, #63b3ed 0%, #4299e1 100%);
  bottom: 30%;
  left: 20%;
  animation-delay: 2s;
}

.orb-3 {
  width: 100px;
  height: 100px;
  background: linear-gradient(45deg, #68d391 0%, #48bb78 100%);
  top: 50%;
  right: 30%;
  animation-delay: 4s;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0px) translateX(0px);
  }
  33% {
    transform: translateY(-20px) translateX(10px);
  }
  66% {
    transform: translateY(10px) translateX(-10px);
  }
}
</style>