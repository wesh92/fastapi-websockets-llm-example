import React from 'react'
import ChatComponent from './components/ChatComponent'

function App() {
  // We wrap our ChatComponent in a div with some basic styling
  return (
    <div className="min-h-screen bg-gray-100 p-4">
      <ChatComponent />
    </div>
  )
}

export default App