'use server'

import { permanentRedirect } from 'next/navigation'

export default async function Page() {
  // Redirect to the main page where the guides now are
  permanentRedirect(`/#get-started`)
}
