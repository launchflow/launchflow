'use client'

import docsDarkLogo from '@/images/launchflow-docs-logo-dark.png'
import docsLightLogo from '@/images/launchflow-docs-logo-light.png'
import launchFlowLogo from '@/images/launchflow-logo.svg'
import clsx from 'clsx'
import Image from 'next/image'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'

import { MobileNavigation } from '@/components/MobileNavigation'
import { Navigation } from '@/components/Navigation'
import { Search } from '@/components/Search'
import { getActiveTab, headerTabs } from '@/lib/headerTabs'
import { Button } from './Button'
import { ThemeSelector } from './ThemeSelector'

const Tabs = () => {
  let activeTab = getActiveTab()
  return (
    <div className="pl-5 text-center text-sm font-medium md:pl-0 dark:text-slate-300">
      <ul className="-mb-px flex flex-wrap">
        {headerTabs.map((tab, index) => (
          <li className="me-2" key={index}>
            <Link
              href={tab.href}
              className={`${
                tab.href == activeTab?.href
                  ? 'border-secondary'
                  : 'border-transparent'
              } hover:border-secondaryogo mr-6 inline-block rounded-t-lg border-b-2 pb-2 hover:text-gray-600 dark:hover:text-gray-300`}
              aria-current={index === 0 ? 'page' : undefined}
            >
              {tab.title}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}

function Header() {
  let [isScrolled, setIsScrolled] = useState(false)

  useEffect(() => {
    function onScroll() {
      setIsScrolled(window.scrollY > 0)
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      window.removeEventListener('scroll', onScroll)
    }
  }, [])

  return (
    <header
      id="mainHeader"
      className={clsx(
        'sticky top-0 z-50  justify-between bg-white shadow-md shadow-background_dark/5 transition duration-500 sm:px-6 lg:px-8 dark:bg-background_dark/95 dark:shadow-none dark:backdrop-blur dark:[@supports(backdrop-filter:blur(0))]:bg-background_dark/75',
        isScrolled
          ? 'dark:bg-background_dark/95 dark:backdrop-blur dark:[@supports(backdrop-filter:blur(0))]:bg-background_dark/75'
          : 'dark:bg-transparent',
      )}
    >
      <div className="flex flex-none flex-wrap items-center justify-between px-4 pb-2 pt-5 sm:px-6 lg:px-8">
        <div className="mr-3 flex lg:hidden">
          <MobileNavigation />
        </div>
        <div className="relative flex flex-grow basis-0 items-center">
          <Link href="/" aria-label="Home page">
            <div className="hidden md:block">
              <Image
                src={docsLightLogo}
                alt="LaunchFlow Logo"
                width={225}
                height={225}
                unoptimized
                priority
                className="block dark:hidden"
              />
              <Image
                src={docsDarkLogo}
                alt="LaunchFlow Logo"
                width={225}
                height={225}
                unoptimized
                priority
                className="hidden dark:block"
              />
            </div>
            <div className="md:hidden">
              <Image
                src={launchFlowLogo}
                alt="LaunchFlow Logo"
                width={25}
                height={25}
                unoptimized
                priority
              />
            </div>
          </Link>
        </div>
        <div className="-my-5 mr-6 sm:mr-8 md:mr-0">
          <Search />
        </div>
        <div className="relative flex basis-0 items-center justify-end gap-6 sm:gap-8 md:flex-grow">
          <ThemeSelector className="relative z-10" />
          <Link
            href="https://join.slack.com/t/launchflowusers/shared_invite/zt-280e6a5ck-zfCrKbqw5w89L~0Xl55G4w"
            className="text-slate hidden items-center border-b border-dashed border-secondary/60 text-sm font-semibold hover:font-bold md:flex dark:text-white"
          >
            <span>Join Slack</span>
            <Image
              src="/images/slack.svg"
              alt="Slack Logo"
              width={30}
              height={30}
              className="block fill-white dark:hidden"
            />
            <Image
              src="/images/slack.svg"
              alt="Slack Logo"
              width={30}
              height={30}
              className="hidden fill-white dark:block"
            />
          </Link>
          <Button
            href="https://console.launchflow.com"
            className="hidden md:block"
          >
            Sign up
          </Button>
        </div>
      </div>
      <div className="pt-2 lg:px-8">
        <Tabs />
      </div>
    </header>
  )
}

export function Layout({ children }: { children: React.ReactNode }) {
  let pathname = usePathname()
  let isHomePage = pathname === '/'

  return (
    <div className="flex w-full flex-col">
      <Header />
      <div className="relative mx-auto flex w-full max-w-8xl flex-auto justify-center sm:px-2 lg:px-8 xl:px-12">
        <div className="hidden lg:relative lg:block lg:flex-none">
          <div className="absolute inset-y-0 right-0 w-[50vw] bg-slate-50 dark:hidden" />
          <div className="absolute bottom-0 right-0 top-16 hidden h-12 w-px bg-gradient-to-t from-slate-800 dark:block" />
          <div className="absolute bottom-0 right-0 top-28 hidden w-px bg-slate-800 dark:block" />
          <div className="sticky top-[4.75rem] -ml-0.5 h-[calc(100vh-4.75rem)] w-64 overflow-y-auto overflow-x-hidden py-16 pl-0.5 pr-8 xl:w-72 xl:pr-16">
            <Navigation />
          </div>
        </div>
        {children}
      </div>
    </div>
  )
}
