import mongoose, { isValidObjectId } from "mongoose"
import { Video } from "../models/video.model.js"
import { User } from "../models/user.model.js"
import { Like } from "../models/like.model.js"
import { ApiError } from "../utils/ApiError.js"
import { ApiResponse } from "../utils/ApiResponse.js"
import { asyncHandler } from "../utils/asyncHandler.js"
import {
    getPersonalizedRecommendations,
    getSimilarVideos,
    syncEmbeddings,
    checkHealth
} from "../utils/recommendationService.js"


/**
 * Get personalized video recommendations for logged-in user
 */
const getRecommendations = asyncHandler(async (req, res) => {
    const { limit = 20 } = req.query
    const userId = req.user._id

    // Get user's watch history
    const user = await User.findById(userId).select("watchHistory")
    const watchedVideoIds = user?.watchHistory?.map(id => id.toString()) || []

    // Get user's liked videos
    const likedDocs = await Like.find({
        likedBy: userId,
        video: { $exists: true, $ne: null }
    }).select("video")
    const likedVideoIds = likedDocs.map(doc => doc.video.toString())

    // If no history, return popular videos as fallback
    if (watchedVideoIds.length === 0 && likedVideoIds.length === 0) {
        const popularVideos = await Video.aggregate([
            { $match: { isPublished: true } },
            { $sort: { views: -1, createdAt: -1 } },
            { $limit: parseInt(limit) },
            {
                $lookup: {
                    from: "users",
                    localField: "owner",
                    foreignField: "_id",
                    as: "owner",
                    pipeline: [
                        { $project: { username: 1, fullName: 1, avatar: 1 } }
                    ]
                }
            },
            { $addFields: { owner: { $first: "$owner" } } }
        ])

        return res
            .status(200)
            .json(
                new ApiResponse(
                    200,
                    {
                        recommendations: popularVideos,
                        fallback: true,
                        reason: "No user history available - showing popular videos"
                    },
                    "Popular videos fetched as fallback"
                )
            )
    }

    // Exclude videos user has already watched or liked
    const excludeVideoIds = [...new Set([...watchedVideoIds, ...likedVideoIds])]

    // Get all published videos for metadata
    const allVideos = await Video.find({ isPublished: true }).select("views createdAt")
    const videoMetadata = {}
    allVideos.forEach(v => {
        videoMetadata[v._id.toString()] = {
            views: v.views || 0,
            created_at: v.createdAt.toISOString()
        }
    })

    // Call recommendation service
    const recommendations = await getPersonalizedRecommendations(
        userId.toString(),
        watchedVideoIds,
        likedVideoIds,
        videoMetadata,
        parseInt(limit),
        excludeVideoIds
    )

    // Fallback if recommendation service fails
    if (!recommendations || !recommendations.recommendations) {
        const fallbackVideos = await Video.aggregate([
            {
                $match: {
                    isPublished: true,
                    _id: { $nin: excludeVideoIds.map(id => new mongoose.Types.ObjectId(id)) }
                }
            },
            { $sort: { views: -1, createdAt: -1 } },
            { $limit: parseInt(limit) },
            {
                $lookup: {
                    from: "users",
                    localField: "owner",
                    foreignField: "_id",
                    as: "owner",
                    pipeline: [
                        { $project: { username: 1, fullName: 1, avatar: 1 } }
                    ]
                }
            },
            { $addFields: { owner: { $first: "$owner" } } }
        ])

        return res
            .status(200)
            .json(
                new ApiResponse(
                    200,
                    {
                        recommendations: fallbackVideos,
                        fallback: true,
                        reason: "Recommendation service unavailable - using popularity fallback"
                    },
                    "Fallback recommendations fetched"
                )
            )
    }

    // Fetch full video details for recommended IDs
    const recommendedIds = recommendations.recommendations.map(r => r.video_id)
    const videos = await Video.aggregate([
        {
            $match: {
                _id: { $in: recommendedIds.map(id => new mongoose.Types.ObjectId(id)) }
            }
        },
        {
            $lookup: {
                from: "users",
                localField: "owner",
                foreignField: "_id",
                as: "owner",
                pipeline: [
                    { $project: { username: 1, fullName: 1, avatar: 1 } }
                ]
            }
        },
        { $addFields: { owner: { $first: "$owner" } } }
    ])

    // Preserve recommendation order and attach scores
    const videoMap = new Map(videos.map(v => [v._id.toString(), v]))
    const orderedResults = recommendations.recommendations
        .filter(r => videoMap.has(r.video_id))
        .map(r => ({
            video: videoMap.get(r.video_id),
            score: r.final_score,
            scoreBreakdown: r.score_breakdown
        }))

    return res
        .status(200)
        .json(
            new ApiResponse(
                200,
                {
                    recommendations: orderedResults,
                    userProfile: {
                        watchedCount: recommendations.watched_count,
                        likedCount: recommendations.liked_count
                    },
                    fallback: false
                },
                "Personalized recommendations fetched successfully"
            )
        )
})


/**
 * Get similar videos to a specific video
 */
const getSimilar = asyncHandler(async (req, res) => {
    const { videoId } = req.params
    const { limit = 10 } = req.query

    if (!isValidObjectId(videoId)) {
        throw new ApiError(400, "Invalid video ID")
    }

    const video = await Video.findById(videoId)
    if (!video) {
        throw new ApiError(404, "Video not found")
    }

    const similarResult = await getSimilarVideos(videoId, parseInt(limit))

    // Fallback: return videos from same owner
    if (!similarResult || !similarResult.similar_videos) {
        const fallbackVideos = await Video.aggregate([
            {
                $match: {
                    isPublished: true,
                    _id: { $ne: new mongoose.Types.ObjectId(videoId) },
                    owner: video.owner
                }
            },
            { $sort: { views: -1 } },
            { $limit: parseInt(limit) },
            {
                $lookup: {
                    from: "users",
                    localField: "owner",
                    foreignField: "_id",
                    as: "owner",
                    pipeline: [
                        { $project: { username: 1, fullName: 1, avatar: 1 } }
                    ]
                }
            },
            { $addFields: { owner: { $first: "$owner" } } }
        ])

        return res
            .status(200)
            .json(
                new ApiResponse(
                    200,
                    {
                        sourceVideo: videoId,
                        similarVideos: fallbackVideos,
                        fallback: true
                    },
                    "Fallback similar videos fetched"
                )
            )
    }

    // Fetch full video details
    const similarIds = similarResult.similar_videos.map(s => s.video_id)
    const videos = await Video.aggregate([
        {
            $match: {
                _id: { $in: similarIds.map(id => new mongoose.Types.ObjectId(id)) }
            }
        },
        {
            $lookup: {
                from: "users",
                localField: "owner",
                foreignField: "_id",
                as: "owner",
                pipeline: [
                    { $project: { username: 1, fullName: 1, avatar: 1 } }
                ]
            }
        },
        { $addFields: { owner: { $first: "$owner" } } }
    ])

    const videoMap = new Map(videos.map(v => [v._id.toString(), v]))
    const orderedResults = similarResult.similar_videos
        .filter(s => videoMap.has(s.video_id))
        .map(s => ({
            video: videoMap.get(s.video_id),
            similarityScore: s.similarity_score
        }))

    return res
        .status(200)
        .json(
            new ApiResponse(
                200,
                {
                    sourceVideo: videoId,
                    similarVideos: orderedResults,
                    fallback: false
                },
                "Similar videos fetched successfully"
            )
        )
})


/**
 * Sync video embeddings with the recommendation service
 */
const syncVideoEmbeddings = asyncHandler(async (req, res) => {
    // Get all published videos
    const videos = await Video.find({ isPublished: true }).select("title description")

    if (videos.length === 0) {
        return res
            .status(200)
            .json(
                new ApiResponse(
                    200,
                    { synced: 0, message: "No videos to sync" },
                    "No videos available for sync"
                )
            )
    }

    // Format for the recommendation service
    const videosForSync = videos.map(v => ({
        video_id: v._id.toString(),
        title: v.title,
        description: v.description
    }))

    // Call sync endpoint
    const result = await syncEmbeddings(videosForSync)

    if (!result) {
        throw new ApiError(503, "Recommendation service unavailable")
    }

    return res
        .status(200)
        .json(
            new ApiResponse(
                200,
                result,
                "Embeddings synced successfully"
            )
        )
})


/**
 * Health check for recommendation service
 */
const getRecommendationHealth = asyncHandler(async (req, res) => {
    const health = await checkHealth()

    const statusCode = health.status === "healthy" ? 200 : 503

    return res
        .status(statusCode)
        .json(
            new ApiResponse(
                statusCode,
                health,
                health.status === "healthy"
                    ? "Recommendation service is healthy"
                    : "Recommendation service is unhealthy"
            )
        )
})


export {
    getRecommendations,
    getSimilar,
    syncVideoEmbeddings,
    getRecommendationHealth
}
