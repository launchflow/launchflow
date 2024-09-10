'use client'
import React from 'react'
import { useGettingStartedContext } from '@/components/GettingStartedSelector' // Import the context

type GettingStartedSectionProps = {
  cloudProvider: string
  runtime?: string | undefined
  children: React.ReactNode
}

export function GettingStartedSection({
  cloudProvider,
  runtime,
  children,
}: GettingStartedSectionProps) {
  const ctx = useGettingStartedContext()

  if (runtime === undefined) {
    if (cloudProvider !== ctx.selectedCloudProvider.name) {
      return null
    }
    return children
  } else {
    if (
      runtime !== ctx.selectedRuntime.name ||
      cloudProvider !== ctx.selectedCloudProvider.name
    ) {
      return null
    }
    return children
  }
}
