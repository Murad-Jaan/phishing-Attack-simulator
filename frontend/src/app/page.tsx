import { en } from '@/content/en'

export default function HomePage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-4">{en.app.name}</h1>
      <p className="text-muted-foreground">Phase 2 - M0 Foundation</p>
    </div>
  )
}
