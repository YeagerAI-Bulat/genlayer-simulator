<script setup lang="ts">
import MainTitle from '@/components/Simulator/MainTitle.vue';
import ProviderSection from '@/components/Simulator/settings/ProviderSection.vue';
import SimulatorSection from '@/components/Simulator/settings/SimulatorSection.vue';
</script>

<template>
  <div class="flex max-h-[93vh] w-full flex-col overflow-y-auto">
    <MainTitle data-testid="settings-page-title">Settings</MainTitle>

    <SimulatorSection />
    <ProviderSection />
  </div>
</template>
