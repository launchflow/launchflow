'use client'

import { Listbox } from '@headlessui/react'
import { CheckIcon, ChevronUpDownIcon } from '@heroicons/react/20/solid'
import clsx from 'clsx'

import Image from 'next/image'
import { createContext, useContext, useEffect, useMemo, useState } from 'react'

type SelectionOption = {
  name: string
  avatar: string
  darkAvatar?: string | undefined
}

const cloudProviders = [
  {
    name: 'AWS',
    avatar: '/images/aws.svg',
    darkAvatar: '/images/aws-dark.svg',
  },
  { name: 'GCP', avatar: '/images/gcp.svg' },
]

const runtimes = {
  AWS: [
    {
      name: 'Lambda',
      avatar: '/images/lambda-icon.svg',
    },
    {
      name: 'ECS Fargate',
      avatar: '/images/aws_fargate.svg',
    },
  ],
  GCP: [
    {
      name: 'Cloud Run',
      avatar: '/images/cloud_run.svg',
    },
    {
      name: 'Compute Engine',
      avatar: '/images/compute_engine.svg',
    },
    {
      name: 'Kubernetes',
      avatar: '/images/k8_logo.svg',
    },
  ],
}

type GettingStartedSelectorProps = {
  awsRuntimeOptions?: string[]
  gcpRuntimeOptions?: string[]
  children: React.ReactNode
}

interface GettingStartedContextType {
  selectedCloudProvider: SelectionOption
  selectedRuntime: SelectionOption
}

const GettingStartedContext = createContext<
  GettingStartedContextType | undefined
>(undefined)

export function useGettingStartedContext() {
  const context = useContext(GettingStartedContext)
  if (!context) {
    throw new Error(
      'useGettingStartedContext must be used within a GettingStartedProvider',
    )
  }
  return context
}

function Selector({
  selected,
  setSelected,
  options,
}: {
  selected: SelectionOption
  setSelected: (item: SelectionOption) => void
  options: SelectionOption[]
}) {
  return (
    <Listbox value={selected} onChange={setSelected}>
      <div className="relative">
        <Listbox.Button className="relative w-full cursor-default rounded-md bg-white py-1.5 pl-3 pr-10 text-left text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:outline-none focus:ring-2 focus:ring-primary sm:text-sm sm:leading-6 dark:bg-background_dark dark:ring-white/5">
          <span className="flex items-center">
            <Image
              height={500}
              width={500}
              alt={`${selected.name} avatar`}
              src={selected.avatar}
              className={clsx(
                'h-5 w-5 flex-shrink-0 rounded-full',
                selected.darkAvatar ? 'dark:hidden' : 'block',
              )}
            />
            {selected.darkAvatar && (
              <Image
                height={500}
                width={500}
                alt={`${selected.name} avatar`}
                src={selected.darkAvatar}
                className="hidden h-5 w-5 flex-shrink-0 rounded-full dark:block"
              />
            )}
            <span className="ml-3 block truncate dark:text-slate-400">
              {selected.name}
            </span>
          </span>
          <span className="pointer-events-none absolute inset-y-0 right-0 ml-3 flex items-center pr-2">
            <ChevronUpDownIcon
              aria-hidden="true"
              className="h-5 w-5 text-gray-400"
            />
          </span>
        </Listbox.Button>

        <Listbox.Options className="absolute z-10 mt-1 max-h-56 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none data-[closed]:data-[leave]:opacity-0 data-[leave]:transition data-[leave]:duration-100 data-[leave]:ease-in sm:text-sm dark:bg-background_dark dark:ring-white/5">
          {options.map((option) => (
            <Listbox.Option
              key={option.name}
              value={option}
              className="group relative cursor-default select-none py-2 pl-3 pr-9 text-gray-900 hover:bg-primary/70 hover:text-white"
            >
              <div className="flex items-center">
                <Image
                  alt={`${option.name} avatar`}
                  height={500}
                  width={500}
                  src={option.avatar}
                  className={clsx(
                    'h-5 w-5 flex-shrink-0 rounded-full',
                    option.darkAvatar ? 'dark:hidden' : 'block',
                  )}
                />
                {option.darkAvatar && (
                  <Image
                    alt={`${option.name} avatar`}
                    height={500}
                    width={500}
                    src={option.darkAvatar}
                    className="hidden h-5 w-5 flex-shrink-0 rounded-full dark:block"
                  />
                )}
                <span
                  className={clsx(
                    'ml-3 block truncate font-normal dark:text-slate-400',
                    option.name == selected.name
                      ? 'font-semibold'
                      : 'font-normal',
                  )}
                >
                  {option.name}
                </span>
              </div>

              {option.name == selected.name && (
                <span className="absolute inset-y-0 right-0 flex items-center pr-4 text-primary">
                  <CheckIcon aria-hidden="true" className="h-5 w-5" />
                </span>
              )}
            </Listbox.Option>
          ))}
        </Listbox.Options>
      </div>
    </Listbox>
  )
}

export function GettingStartedSelector({
  awsRuntimeOptions,
  gcpRuntimeOptions,
  children,
}: GettingStartedSelectorProps) {
  const availableCloudProviders: SelectionOption[] = []
  if (awsRuntimeOptions === undefined || awsRuntimeOptions.length > 0) {
    availableCloudProviders.push(cloudProviders[0])
  }
  if (gcpRuntimeOptions === undefined || gcpRuntimeOptions.length > 0) {
    availableCloudProviders.push(cloudProviders[1])
  }
  if (availableCloudProviders.length === 0) {
    throw new Error('No cloud providers available')
  }
  const [selectedCloudProvider, setSelectedCloudProvider] = useState(
    availableCloudProviders[0],
  )

  const availableAwsRutimeOptions = useMemo(() => {
    return runtimes.AWS.filter(
      (runtime) =>
        awsRuntimeOptions === undefined ||
        awsRuntimeOptions.includes(runtime.name),
    )
  }, [awsRuntimeOptions])
  const availableGcpRutimeOptions = useMemo(() => {
    return runtimes.GCP.filter(
      (runtime) =>
        gcpRuntimeOptions === undefined ||
        gcpRuntimeOptions.includes(runtime.name),
    )
  }, [gcpRuntimeOptions])

  const [runtimeOptions, setRunttimeOptions] = useState<SelectionOption[]>(
    selectedCloudProvider.name === 'AWS'
      ? availableAwsRutimeOptions
      : availableGcpRutimeOptions,
  )
  const [selectedRuntime, setSelectedRuntime] = useState(runtimeOptions[0])

  function changeCloudProvider(selected: SelectionOption) {
    setSelectedCloudProvider(selected)
    if (selected.name === 'AWS') {
      setRunttimeOptions(availableAwsRutimeOptions)
      setSelectedRuntime(availableAwsRutimeOptions[0])
    } else {
      setRunttimeOptions(availableGcpRutimeOptions)
      setSelectedRuntime(availableGcpRutimeOptions[0])
    }
    localStorage.setItem('selectedCloudProvider', selected.name)
  }

  function changeRuntime(selected: SelectionOption) {
    setSelectedRuntime(selected)
    localStorage.setItem('selectedRuntime', selected.name)
  }

  useEffect(() => {
    const savedCloudProvider = localStorage.getItem('selectedCloudProvider')
    const savedRuntime = localStorage.getItem('selectedRuntime')

    let tempRuntimeOptions = runtimeOptions

    if (savedCloudProvider) {
      const cloudProvider = availableCloudProviders.find(
        (cp) => cp.name === savedCloudProvider,
      )
      if (cloudProvider) {
        setSelectedCloudProvider(cloudProvider)
        tempRuntimeOptions =
          cloudProvider.name === 'AWS'
            ? availableAwsRutimeOptions
            : availableGcpRutimeOptions
        setRunttimeOptions(tempRuntimeOptions)
        setSelectedRuntime(
          cloudProvider.name === 'AWS'
            ? availableAwsRutimeOptions[0]
            : availableGcpRutimeOptions[0],
        )
      }
    }

    if (savedRuntime) {
      const runtime = tempRuntimeOptions.find((r) => r.name === savedRuntime)
      if (runtime) {
        setSelectedRuntime(runtime)
      }
    }
  }, [])

  return (
    <GettingStartedContext.Provider
      value={{
        selectedCloudProvider,
        selectedRuntime,
      }}
    >
      <div className="not-prose sticky top-[92px] z-10 -mx-4 w-auto bg-slate-50 p-1 px-4 py-2 md:top-[109px] lg:-mx-8 lg:pl-8 xl:-ml-16 xl:-mr-14 xl:pl-16 dark:bg-slate-800">
        <div className="flex space-x-2">
          <div>
            <Selector
              selected={selectedCloudProvider}
              setSelected={changeCloudProvider}
              options={availableCloudProviders}
            />
          </div>
          <div className="flex-grow md:w-64 md:flex-grow-0">
            <Selector
              selected={selectedRuntime}
              setSelected={changeRuntime}
              options={runtimeOptions}
            />
          </div>
        </div>
      </div>
      {children}
    </GettingStartedContext.Provider>
  )
}
