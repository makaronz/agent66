import React, { useState } from 'react'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Checkbox } from './ui/checkbox'
import { Badge } from './ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs'

export const UITestPage = () => {
  const [checkboxChecked, setCheckboxChecked] = useState(false)
  const [inputValue, setInputValue] = useState('')
  const [selectedValue, setSelectedValue] = useState('option1')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [activeTab, setActiveTab] = useState('tab1')

  return (
    <div className="p-8 space-y-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-8">Simplified UI Components Test</h1>

      {/* Buttons Test */}
      <Card>
        <CardHeader>
          <CardTitle>Buttons</CardTitle>
          <CardDescription>Testing different button variants and sizes</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Button variant="default">Default</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="outline">Outline</Button>
            <Button variant="destructive">Destructive</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="link">Link</Button>
          </div>
          <div className="flex gap-2 items-center">
            <Button size="sm">Small</Button>
            <Button size="default">Default</Button>
            <Button size="lg">Large</Button>
            <Button size="icon">🔧</Button>
          </div>
        </CardContent>
      </Card>

      {/* Form Controls Test */}
      <Card>
        <CardHeader>
          <CardTitle>Form Controls</CardTitle>
          <CardDescription>Testing input, label, and checkbox components</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="test-input">Test Input</Label>
            <Input
              id="test-input"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Enter some text..."
            />
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              checked={checkboxChecked}
              onCheckedChange={setCheckboxChecked}
            />
            <Label>Check me</Label>
          </div>

          <div className="space-y-2">
            <Label htmlFor="test-select">Native Select (Simplified)</Label>
            <select
              id="test-select"
              value={selectedValue}
              onChange={(e) => setSelectedValue(e.target.value)}
              className="flex h-10 w-full items-center justify-between rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <option value="option1">Option 1</option>
              <option value="option2">Option 2</option>
              <option value="option3">Option 3</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Badges Test */}
      <Card>
        <CardHeader>
          <CardTitle>Badges</CardTitle>
          <CardDescription>Testing different badge variants</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Badge>Default</Badge>
            <Badge variant="secondary">Secondary</Badge>
            <Badge variant="destructive">Destructive</Badge>
            <Badge variant="outline">Outline</Badge>
          </div>
        </CardContent>
      </Card>

      {/* Dialog Test */}
      <Card>
        <CardHeader>
          <CardTitle>Dialog</CardTitle>
          <CardDescription>Testing simplified dialog component</CardDescription>
        </CardHeader>
        <CardContent>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button>Open Dialog</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Dialog Title</DialogTitle>
                <DialogDescription>
                  This is a simplified dialog component using basic HTML and CSS.
                  No Radix UI dependencies!
                </DialogDescription>
              </DialogHeader>
              <div className="py-4">
                <p>Dialog content goes here. The dialog can be closed by clicking the X button or the backdrop.</p>
              </div>
            </DialogContent>
          </Dialog>
        </CardContent>
      </Card>

      {/* Tabs Test */}
      <Card>
        <CardHeader>
          <CardTitle>Tabs</CardTitle>
          <CardDescription>Testing simplified tabs component</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList>
              <TabsTrigger value="tab1">Tab 1</TabsTrigger>
              <TabsTrigger value="tab2">Tab 2</TabsTrigger>
              <TabsTrigger value="tab3">Tab 3</TabsTrigger>
            </TabsList>
            <TabsContent value="tab1">
              <p>Content for Tab 1 - No Radix UI dependencies!</p>
            </TabsContent>
            <TabsContent value="tab2">
              <p>Content for Tab 2 - Using simple React state management.</p>
            </TabsContent>
            <TabsContent value="tab3">
              <p>Content for Tab 3 - Clean and simple implementation.</p>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Summary</CardTitle>
          <CardDescription>Simplification results</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <p><strong>✅ Removed dependencies:</strong></p>
            <ul className="list-disc list-inside space-y-1 text-sm text-gray-600">
              <li>@radix-ui/react-dialog</li>
              <li>@radix-ui/react-checkbox</li>
              <li>@radix-ui/react-select</li>
              <li>@radix-ui/react-tabs</li>
              <li>@radix-ui/react-label</li>
              <li>@radix-ui/react-slot</li>
              <li>class-variance-authority</li>
            </ul>
            <p className="mt-4"><strong>✅ Benefits:</strong></p>
            <ul className="list-disc list-inside space-y-1 text-sm text-gray-600">
              <li>Smaller bundle size</li>
              <li>Simpler codebase</li>
              <li>Easier to customize</li>
              <li>Fewer dependencies</li>
              <li>Better for small teams</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default UITestPage