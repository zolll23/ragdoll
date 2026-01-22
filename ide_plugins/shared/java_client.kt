/**
 * Kotlin/Java API Client for CodeRAG IDE Integration
 * For use in PhpStorm plugins
 */
package com.coderag.ide.client

import com.google.gson.Gson
import com.google.gson.annotations.SerializedName
import java.net.HttpURLConnection
import java.net.URL
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter

/**
 * CodeRAG API Client
 */
class CodeRAGClient(
    private val baseUrl: String = "http://localhost:8000",
    private val timeout: Int = 30000
) {
    private val gson = Gson()
    
    /**
     * Make HTTP request
     */
    private fun <T> request(
        method: String,
        endpoint: String,
        body: Any? = null,
        responseClass: Class<T>
    ): T {
        val url = URL("$baseUrl$endpoint")
        val connection = url.openConnection() as HttpURLConnection
        
        try {
            connection.requestMethod = method
            connection.connectTimeout = timeout
            connection.readTimeout = timeout
            connection.setRequestProperty("Content-Type", "application/json")
            connection.setRequestProperty("Accept", "application/json")
            
            if (body != null && (method == "POST" || method == "PUT")) {
                connection.doOutput = true
                val outputStream = OutputStreamWriter(connection.outputStream)
                outputStream.write(gson.toJson(body))
                outputStream.flush()
                outputStream.close()
            }
            
            val responseCode = connection.responseCode
            if (responseCode !in 200..299) {
                val errorStream = connection.errorStream
                val errorReader = BufferedReader(InputStreamReader(errorStream))
                val errorResponse = errorReader.readText()
                throw Exception("API request failed: $responseCode - $errorResponse")
            }
            
            val inputStream = connection.inputStream
            val reader = BufferedReader(InputStreamReader(inputStream))
            val response = reader.readText()
            
            return gson.fromJson(response, responseClass)
        } finally {
            connection.disconnect()
        }
    }
    
    /**
     * Check API health
     */
    fun healthCheck(): HealthResponse {
        return request("GET", "/api/ide/health", null, HealthResponse::class.java)
    }
    
    /**
     * List all indexed projects
     */
    fun listProjects(): List<ProjectInfo> {
        val response = request("GET", "/api/ide/projects", null, Array<ProjectInfo>::class.java)
        return response.toList()
    }
    
    /**
     * Find entity by file location
     */
    fun findEntity(
        projectId: Int,
        filePath: String,
        lineNumber: Int? = null
    ): EntityResponse {
        val request = FindEntityRequest(projectId, filePath, lineNumber)
        return request("POST", "/api/ide/find-entity", request, EntityResponse::class.java)
    }
    
    /**
     * Analyze entity
     */
    fun analyzeEntity(
        entityId: Int? = null,
        projectId: Int? = null,
        filePath: String? = null,
        entityName: String? = null,
        lineNumber: Int? = null
    ): EntityResponse {
        val request = AnalyzeEntityRequest(entityId, projectId, filePath, entityName, lineNumber)
        return request("POST", "/api/ide/analyze", request, EntityResponse::class.java)
    }
    
    /**
     * Search code
     */
    fun searchCode(
        query: String,
        projectId: Int? = null,
        limit: Int = 20
    ): List<SearchResult> {
        val request = SearchRequest(query, projectId, limit)
        val response = request("POST", "/api/ide/search", request, Array<SearchResult>::class.java)
        return response.toList()
    }
    
    /**
     * Get refactoring suggestions
     */
    fun getRefactoringSuggestions(
        entityId: Int,
        includeSimilarCode: Boolean = true,
        similarityThreshold: Double = 0.7
    ): RefactoringResponse {
        val request = RefactoringRequest(entityId, includeSimilarCode, similarityThreshold)
        return request("POST", "/api/ide/refactoring", request, RefactoringResponse::class.java)
    }
    
    /**
     * Get entity metrics
     */
    fun getEntityMetrics(entityId: Int): MetricsResponse {
        return request("GET", "/api/ide/entity/$entityId/metrics", null, MetricsResponse::class.java)
    }
}

// Data classes

data class HealthResponse(
    val status: String,
    val service: String
)

data class ProjectInfo(
    val id: Int,
    val name: String,
    val path: String,
    val language: String,
    val totalFiles: Int,
    val indexedFiles: Int,
    val totalEntities: Int,
    val isIndexing: Boolean,
    val progressPercent: Double
)

data class FindEntityRequest(
    val projectId: Int,
    val filePath: String,
    val lineNumber: Int? = null
)

data class AnalyzeEntityRequest(
    val entityId: Int? = null,
    val projectId: Int? = null,
    val filePath: String? = null,
    val entityName: String? = null,
    val lineNumber: Int? = null
)

data class SearchRequest(
    val query: String,
    val projectId: Int? = null,
    val limit: Int = 20
)

data class RefactoringRequest(
    val entityId: Int,
    val includeSimilarCode: Boolean = true,
    val similarityThreshold: Double = 0.7
)

data class EntityInfo(
    val id: Int,
    val name: String,
    val type: String,
    val filePath: String,
    val startLine: Int,
    val endLine: Int,
    val fullQualifiedName: String?,
    val code: String
)

data class AnalysisInfo(
    val id: Int?,
    val description: String,
    val complexity: String,
    val complexityExplanation: String?,
    val solidViolations: List<Map<String, Any>>,
    val designPatterns: List<String>,
    val dddRole: String?,
    val mvcRole: String?,
    val isTestable: Boolean,
    val testabilityScore: Double,
    val testabilityIssues: List<String>
)

data class EntityResponse(
    val entity: EntityInfo,
    val analysis: AnalysisInfo?,
    val dependencies: List<DependencyInfo>,
    val metrics: Map<String, Any>?
)

data class DependencyInfo(
    val id: Int,
    val type: String,
    val dependsOnName: String,
    val dependsOnEntityId: Int?,
    val dependsOnEntity: EntityInfo?
)

data class SearchResult(
    val entityId: Int,
    val name: String,
    val type: String,
    val filePath: String,
    val startLine: Int,
    val endLine: Int,
    val fullQualifiedName: String?,
    val description: String?,
    val complexity: String?,
    val score: Double,
    val matchType: String
)

data class RefactoringSuggestion(
    val type: String,
    val principle: String?,
    val description: String,
    val severity: String,
    val suggestion: String?,
    val location: Location?
)

data class Location(
    val filePath: String?,
    val startLine: Int,
    val endLine: Int
)

data class RefactoringResponse(
    val entityId: Int,
    val entityName: String,
    val filePath: String?,
    val suggestions: List<RefactoringSuggestion>,
    val similarCode: List<Any>
)

data class MetricsResponse(
    val entityId: Int,
    val entityName: String,
    val metrics: MetricsInfo
)

data class MetricsInfo(
    val size: SizeMetrics,
    val complexity: ComplexityMetrics,
    val coupling: CouplingMetrics,
    val quality: QualityMetrics,
    val issues: IssuesMetrics
)

data class SizeMetrics(
    val linesOfCode: Int?,
    val parameterCount: Int?
)

data class ComplexityMetrics(
    val cyclomatic: Int?,
    val cognitive: Int?,
    val maxNestingDepth: Int?,
    val asymptotic: String?,
    val space: String?
)

data class CouplingMetrics(
    val couplingScore: Double?,
    val cohesionScore: Double?,
    val afferentCoupling: Int?,
    val efferentCoupling: Int?
)

data class QualityMetrics(
    val isTestable: Boolean?,
    val testabilityScore: Double?,
    val isGodObject: Boolean?,
    val featureEnvyScore: Double?,
    val longParameterList: Boolean?
)

data class IssuesMetrics(
    val securityIssuesCount: Int,
    val nPlusOneQueriesCount: Int,
    val solidViolationsCount: Int
)



