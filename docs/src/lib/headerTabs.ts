import { homeNavigation, referenceNavigation } from '@/lib/navigation'
import { usePathname } from 'next/navigation';


export type Tab = {
    title: string;
    href: string;
    sideBarNav: string
}

export const headerTabs = [
    { title: "Home", href: "/", "id": "home", sideBarNav: homeNavigation },
    { title: "Reference", href: "/reference", "id": "reference", sideBarNav: referenceNavigation },
]

export function getActiveTab() {
    const pathName = usePathname()
    const isHomePage = pathName === "/" || pathName.startsWith("/docs");
    const isActive = (tabHref: string) => {
        if (tabHref === "/") {
            return isHomePage;
        }
        return pathName.startsWith(tabHref);
    };
    let activeTab = headerTabs.find((tab) => isActive(tab.href));
    return activeTab
}
