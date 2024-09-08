'use client'
import React from 'react'
import { GettingStartedContext } from '@/components/GettingStartedSelector' // Import the context

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
  const ctx = React.useContext(GettingStartedContext)

  if (cloudProvider !== ctx.selectedCloudProvider.name) {
    return null
  }

  return children
}
