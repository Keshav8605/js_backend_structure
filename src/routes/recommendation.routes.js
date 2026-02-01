import { Router } from "express"
import {
    getRecommendations,
    getSimilar,
    syncVideoEmbeddings,
    getRecommendationHealth
} from "../controllers/recommendation.controller.js"
import { verifyJWT } from "../middlewares/auth.middleware.js"

const router = Router()

// Health check (public)
router.route("/health").get(getRecommendationHealth)

// Protected routes
router.use(verifyJWT)

// Get personalized recommendations for the logged-in user
router.route("/personalized").get(getRecommendations)

// Get videos similar to a specific video
router.route("/similar/:videoId").get(getSimilar)

// Sync embeddings (admin operation)
router.route("/sync").post(syncVideoEmbeddings)

export default router
