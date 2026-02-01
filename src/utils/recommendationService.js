import axios from "axios"

const RECOMMENDATION_SERVICE_URL = process.env.RECOMMENDATION_SERVICE_URL || "http://localhost:8001"
const RECOMMENDATION_TIMEOUT = parseInt(process.env.RECOMMENDATION_TIMEOUT_MS) || 10000

const recommendationClient = axios.create({
    baseURL: RECOMMENDATION_SERVICE_URL,
    timeout: RECOMMENDATION_TIMEOUT,
    headers: {
        "Content-Type": "application/json"
    }
})

/**
 * Get personalized recommendations for a user
 * @param {string} userId - User's MongoDB ObjectId
 * @param {string[]} watchedVideoIds - Array of watched video IDs
 * @param {string[]} likedVideoIds - Array of liked video IDs
 * @param {Object} videoMetadata - Metadata for scoring { videoId: { views, created_at } }
 * @param {number} limit - Number of recommendations to return
 * @param {string[]} excludeVideoIds - Videos to exclude from results
 * @returns {Promise<Object|null>} Recommendations with scores and breakdowns, or null on error
 */
const getPersonalizedRecommendations = async (
    userId,
    watchedVideoIds,
    likedVideoIds,
    videoMetadata,
    limit = 20,
    excludeVideoIds = []
) => {
    try {
        const response = await recommendationClient.post("/recommendations/personalized", {
            user_id: userId,
            watched_video_ids: watchedVideoIds,
            liked_video_ids: likedVideoIds,
            video_metadata: videoMetadata,
            limit,
            exclude_video_ids: excludeVideoIds
        })
        return response.data
    } catch (error) {
        console.error("Recommendation service error:", error.message)
        return null
    }
}

/**
 * Get similar videos to a given video
 * @param {string} videoId - Video's MongoDB ObjectId
 * @param {number} limit - Number of similar videos to return
 * @returns {Promise<Object|null>} Similar videos with similarity scores, or null on error
 */
const getSimilarVideos = async (videoId, limit = 10) => {
    try {
        const response = await recommendationClient.get(`/recommendations/similar/${videoId}`, {
            params: { limit }
        })
        return response.data
    } catch (error) {
        console.error("Similar videos service error:", error.message)
        return null
    }
}

/**
 * Submit videos for batch embedding generation
 * @param {Array<{video_id: string, title: string, description: string}>} videos
 * @returns {Promise<Object|null>} Batch processing result, or null on error
 */
const submitBatchEmbeddings = async (videos) => {
    try {
        const response = await recommendationClient.post("/embeddings/batch", { videos })
        return response.data
    } catch (error) {
        console.error("Embedding batch submission error:", error.message)
        return null
    }
}

/**
 * Sync embeddings for all provided videos (only generates for new videos)
 * @param {Array<{video_id: string, title: string, description: string}>} videos
 * @returns {Promise<Object|null>} Sync result with stats, or null on error
 */
const syncEmbeddings = async (videos) => {
    try {
        const response = await recommendationClient.post("/embeddings/sync", { videos })
        return response.data
    } catch (error) {
        console.error("Embedding sync error:", error.message)
        return null
    }
}

/**
 * Delete embedding for a specific video
 * @param {string} videoId - Video ID to remove from index
 * @returns {Promise<Object|null>} Deletion result, or null on error
 */
const deleteEmbedding = async (videoId) => {
    try {
        const response = await recommendationClient.delete(`/embeddings/${videoId}`)
        return response.data
    } catch (error) {
        console.error("Embedding deletion error:", error.message)
        return null
    }
}

/**
 * Check recommendation service health
 * @returns {Promise<Object>} Health status
 */
const checkHealth = async () => {
    try {
        const response = await recommendationClient.get("/health")
        return response.data
    } catch (error) {
        console.error("Recommendation service health check failed:", error.message)
        return { status: "unhealthy", error: error.message }
    }
}

export {
    getPersonalizedRecommendations,
    getSimilarVideos,
    submitBatchEmbeddings,
    syncEmbeddings,
    deleteEmbedding,
    checkHealth
}
