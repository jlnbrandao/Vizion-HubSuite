import { computed, ref } from 'vue'

export function usePlatform() {
  const platform = ref('web')
  const isNative = computed(() => false)
  const isWeb = computed(() => true)
  const isIOS = computed(() => false)
  const isAndroid = computed(() => false)
  const isMobile = computed(() => false)

  return { platform, isNative, isWeb, isIOS, isAndroid, isMobile }
}
