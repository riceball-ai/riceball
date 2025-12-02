<script setup lang="ts">
import { ref, computed } from 'vue'
import { ArrowLeft, Save, Sparkles } from 'lucide-vue-next'
import { Button } from '~/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card'
import { Input } from '~/components/ui/input'
import { Label } from '~/components/ui/label'
import { Textarea } from '~/components/ui/textarea'
import { Badge } from '~/components/ui/badge'
import { toast } from 'vue-sonner'

const { t } = useI18n()

definePageMeta({
  layout: 'admin',
  breadcrumb: 'admin.pages.assistants.translations.breadcrumb'
})

const route = useRoute()
const router = useRouter()
const assistantId = route.params.id as string

// Fetch translation data
const { data: translationData, refresh, pending } = await useAPI<any>(
  `/v1/admin/assistants/${assistantId}/translations`,
  { server: false }
)

// Create computed property for reactive unpacking
const assistantData = computed(() => translationData.value || {})

// Currently selected locale
const selectedLocale = ref('zh-Hans')
const isSaving = ref(false)

// Available locales
const availableLocales = computed(() => [
  { code: 'zh-Hans', label: '简体中文', flag: '🇨🇳' },
  { code: 'zh-Hant', label: '繁體中文', flag: '🇭🇰' },
  { code: 'ja', label: '日本語', flag: '🇯🇵' },
  { code: 'ko', label: '한국어', flag: '🇰🇷' },
  { code: 'es', label: 'Español', flag: '🇪🇸' },
  { code: 'fr', label: 'Français', flag: '🇫🇷' },
  { code: 'de', label: 'Deutsch', flag: '🇩🇪' }
])

// Current translation data (reactive)
const currentTranslation = ref({
  name: '',
  description: '',
  system_prompt: ''
})

// Watch locale change, load corresponding translation
watch(selectedLocale, (newLocale) => {
  if (translationData.value?.translations?.[newLocale]) {
    currentTranslation.value = {
      name: translationData.value.translations[newLocale].name || '',
      description: translationData.value.translations[newLocale].description || '',
      system_prompt: translationData.value.translations[newLocale].system_prompt || ''
    }
  } else {
    // Clear form
    currentTranslation.value = {
      name: '',
      description: '',
      system_prompt: ''
    }
  }
}, { immediate: true })

// Save translation
const saveTranslation = async () => {
  isSaving.value = true
  try {
    const { $api } = useNuxtApp()
    await $api(
      `/v1/admin/assistants/${assistantId}/translations/${selectedLocale.value}`,
      {
        method: 'PUT',
        body: currentTranslation.value
      }
    )
    toast.success(t('admin.pages.assistants.translations.saveSuccess'))
    await refresh()
  } catch (error) {
    console.error('Save failed:', error)
    toast.error(t('admin.pages.assistants.translations.saveFailed'))
  } finally {
    isSaving.value = false
  }
}

// Return to assistant details
const goBack = () => {
  router.push(`/admin/assistants/${assistantId}`)
}
</script>

<template>
  <div class="container mx-auto py-6 space-y-6">
    <!-- Loading state -->
    <div v-if="pending" class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
    </div>

    <!-- Data loaded -->
    <template v-else-if="translationData">
      <!-- Page header and actions -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold">{{ t('admin.pages.assistants.translations.title') }}</h1>
        <p class="text-muted-foreground">
          {{ t('admin.pages.assistants.translations.subtitle', { name: assistantData.default_name || t('common.loading') }) }}
        </p>
      </div>
      <div class="flex gap-2">
        <Button variant="outline" @click="goBack">
          <ArrowLeft class="h-4 w-4 mr-2" />
          {{ t('admin.back') }}
        </Button>
        <Button @click="saveTranslation" :disabled="isSaving">
          <Save class="h-4 w-4 mr-2" />
          {{ isSaving ? t('admin.pages.assistants.translations.saving') : t('admin.pages.assistants.translations.save') }}
        </Button>
      </div>
    </div>

    <div class="grid grid-cols-12 gap-6">
      <!-- Left: Language List -->
      <Card class="col-span-3">
        <CardHeader>
          <CardTitle>{{ t('admin.pages.assistants.translations.languageList') }}</CardTitle>
          <CardDescription>{{ t('admin.pages.assistants.translations.selectLanguage') }}</CardDescription>
        </CardHeader>
        <CardContent class="space-y-2">
          <!-- Default Language (Read-only) -->
          <div class="p-3 border rounded-lg bg-muted/50">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="text-lg">🇺🇸</span>
                <div>
                  <div class="font-medium text-sm">English</div>
                  <div class="text-xs text-muted-foreground">{{ t('admin.pages.assistants.translations.defaultLanguage') }}</div>
                </div>
              </div>
              <Badge variant="outline" class="text-xs">100%</Badge>
            </div>
          </div>

          <!-- Translatable Languages -->
          <div
            v-for="locale in availableLocales"
            :key="locale.code"
            class="p-3 border rounded-lg cursor-pointer hover:bg-muted/50 transition-colors"
            :class="{ 
              'bg-primary/10 border-primary': selectedLocale === locale.code,
              'bg-background': selectedLocale !== locale.code
            }"
            @click="selectedLocale = locale.code"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="text-lg">{{ locale.flag }}</span>
                <div class="text-sm font-medium">{{ locale.label }}</div>
              </div>
              <!-- Translation Progress -->
              <Badge
                :variant="
                  (assistantData.translation_progress?.[locale.code] || 0) === 100
                    ? 'default'
                    : (assistantData.translation_progress?.[locale.code] || 0) > 0
                    ? 'secondary'
                    : 'outline'
                "
                class="text-xs"
              >
                {{ assistantData.translation_progress?.[locale.code] || 0 }}%
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Right: Translation Editor -->
      <div class="col-span-9 space-y-6">
        <!-- Current Language Info -->
        <Card>
          <CardHeader>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <span class="text-3xl">
                  {{ availableLocales.find(l => l.code === selectedLocale)?.flag }}
                </span>
                <div>
                  <CardTitle>
                    {{ availableLocales.find(l => l.code === selectedLocale)?.label }}
                  </CardTitle>
                  <CardDescription>
                    {{ t('admin.pages.assistants.translations.progress', { progress: assistantData.translation_progress?.[selectedLocale] || 0 }) }}
                  </CardDescription>
                </div>
              </div>
              <!-- <div class="flex gap-2">
                <Button variant="outline" size="sm" disabled>
                  <Sparkles class="h-4 w-4 mr-2" />
                  AI translation (coming soon)
                </Button>
              </div> -->
            </div>
          </CardHeader>
          <CardContent class="space-y-6">
            <!-- Translation Comparison Area -->
            <div class="grid grid-cols-2 gap-6">
              <!-- Left: Default Language (Reference) -->
              <div class="space-y-4">
                <div class="flex items-center gap-2 mb-2">
                  <span class="text-lg">🇺🇸</span>
                  <h3 class="font-semibold">{{ t('admin.pages.assistants.translations.reference') }}</h3>
                </div>
                
                <div class="space-y-2">
                  <Label class="text-xs text-muted-foreground">{{ t('admin.pages.assistants.create.basicInfo.nameLabel') }}</Label>
                  <Input
                    v-model="assistantData.default_name"
                    readonly
                    class="bg-muted/50"
                  />
                </div>
                
                <div class="space-y-2">
                  <Label class="text-xs text-muted-foreground">{{ t('admin.pages.assistants.create.basicInfo.descriptionLabel') }}</Label>
                  <Textarea
                    v-model="assistantData.default_description"
                    readonly
                    class="bg-muted/50 resize-none"
                    :rows="4"
                  />
                </div>
                
                <div class="space-y-2">
                  <Label class="text-xs text-muted-foreground">{{ t('admin.pages.assistants.create.modelConfig.systemPromptLabel') }}</Label>
                  <Textarea
                    v-model="assistantData.default_system_prompt"
                    readonly
                    class="bg-muted/50 font-mono text-xs resize-none"
                    :rows="12"
                  />
                </div>
              </div>

              <!-- Right: Current Language (Editable) -->
              <div class="space-y-4">
                <div class="flex items-center gap-2 mb-2">
                  <span class="text-lg">
                    {{ availableLocales.find(l => l.code === selectedLocale)?.flag }}
                  </span>
                  <h3 class="font-semibold">
                    {{ t('admin.pages.assistants.translations.translation', { language: availableLocales.find(l => l.code === selectedLocale)?.label }) }}
                  </h3>
                </div>
                
                <div class="space-y-2">
                  <Label>{{ t('admin.pages.assistants.create.basicInfo.nameLabel') }} *</Label>
                  <Input
                    v-model="currentTranslation.name"
                    :placeholder="t('admin.pages.assistants.translations.namePlaceholder')"
                  />
                </div>
                
                <div class="space-y-2">
                  <Label>{{ t('admin.pages.assistants.create.basicInfo.descriptionLabel') }} *</Label>
                  <Textarea
                    v-model="currentTranslation.description"
                    :placeholder="t('admin.pages.assistants.translations.descPlaceholder')"
                    class="resize-none"
                    :rows="4"
                  />
                </div>
                
                <div class="space-y-2">
                  <Label>{{ t('admin.pages.assistants.create.modelConfig.systemPromptLabel') }} *</Label>
                  <Textarea
                    v-model="currentTranslation.system_prompt"
                    :placeholder="t('admin.pages.assistants.translations.promptPlaceholder')"
                    class="font-mono text-xs resize-none"
                    :rows="12"
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <!-- Translation Guide -->
        <Card>
          <CardHeader>
            <CardTitle class="text-base">{{ t('admin.pages.assistants.translations.guideTitle') }}</CardTitle>
          </CardHeader>
          <CardContent class="text-sm text-muted-foreground space-y-2">
            <p>{{ t('admin.pages.assistants.translations.guide1') }}</p>
            <p>{{ t('admin.pages.assistants.translations.guide2') }}</p>
            <p>{{ t('admin.pages.assistants.translations.guide3') }}</p>
            <p>{{ t('admin.pages.assistants.translations.guide4') }}</p>
          </CardContent>
        </Card>
      </div>
    </div>
    </template>

    <!-- Error State -->
    <div v-else class="text-center py-12">
      <p class="text-destructive">{{ t('admin.pages.assistants.translations.loadFailed') }}</p>
    </div>
  </div>
</template>
