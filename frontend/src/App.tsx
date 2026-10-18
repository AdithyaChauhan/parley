import { Button } from "@/components/ui/button"

// Test page: checks that Parley's font, colors and corners work
function App() {
  return (
    <main className="flex min-h-svh items-center justify-center p-6">
      <div className="flex flex-col items-center gap-6 rounded-card bg-card p-8 shadow-sm">
        <h1 className="text-header font-semibold">Parley</h1>
        <Button>Start chatting</Button>
      </div>
    </main>
  )
}

export default App
