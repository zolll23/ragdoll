import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import SearchPage from './pages/SearchPage'
import ProjectsPage from './pages/ProjectsPage'
import EntitiesPage from './pages/EntitiesPage'
import EntityDetailPage from './pages/EntityDetailPage'
import ProvidersPage from './pages/ProvidersPage'
import SimilarCodePage from './pages/SimilarCodePage'
import FilesPage from './pages/FilesPage'
import RagdollPage from './pages/RagdollPage'

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/projects" element={<ProjectsPage />} />
            <Route path="/projects/:projectId/entities" element={<EntitiesPage />} />
            <Route path="/projects/:projectId/files" element={<FilesPage />} />
            <Route path="/entities/:entityId" element={<EntityDetailPage />} />
          <Route path="/similar-code" element={<SimilarCodePage />} />
            <Route path="/providers" element={<ProvidersPage />} />
            <Route path="/ragdoll" element={<RagdollPage />} />
            <Route path="/goose" element={<RagdollPage />} />
          </Routes>
        </Layout>
      </Router>
    </QueryClientProvider>
  )
}

export default App

