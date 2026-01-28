import mongoose, {isValidObjectId} from "mongoose"
import {Video} from "../models/video.model.js"
import {User} from "../models/user.model.js"
import {ApiError} from "../utils/ApiError.js"
import {ApiResponse} from "../utils/ApiResponse.js"
import {asyncHandler} from "../utils/asyncHandler.js"
import {uploadOnCloudinary} from "../utils/cloudinary.js"


const getAllVideos = asyncHandler(async (req, res) => {
    const { page = 1, limit = 10, query, sortBy, sortType, userId } = req.query

    // Build match conditions
    const matchConditions = {
        isPublished: true
    }

    // Add user filter if userId is provided
    if (userId) {
        if (!isValidObjectId(userId)) {
            throw new ApiError(400, "Invalid user ID")
        }
        matchConditions.owner = new mongoose.Types.ObjectId(userId)
    }

    // Add search query if provided
    if (query) {
        matchConditions.$or = [
            { title: { $regex: query, $options: "i" } },
            { description: { $regex: query, $options: "i" } }
        ]
    }

    // Build sort options
    const sortOptions = {}
    if (sortBy && sortType) {
        sortOptions[sortBy] = sortType === "asc" ? 1 : -1
    } else {
        sortOptions.createdAt = -1
    }

    // Create aggregation pipeline
    const videoAggregate = Video.aggregate([
        {
            $match: matchConditions
        },
        {
            $lookup: {
                from: "users",
                localField: "owner",
                foreignField: "_id",
                as: "owner",
                pipeline: [
                    {
                        $project: {
                            username: 1,
                            fullName: 1,
                            avatar: 1
                        }
                    }
                ]
            }
        },
        {
            $addFields: {
                owner: {
                    $first: "$owner"
                }
            }
        },
        {
            $sort: sortOptions
        }
    ])

    const options = {
        page: parseInt(page, 10),
        limit: parseInt(limit, 10)
    }

    const videos = await Video.aggregatePaginate(videoAggregate, options)

    return res
        .status(200)
        .json(
            new ApiResponse(200, videos, "Videos fetched successfully")
        )
})

const publishAVideo = asyncHandler(async (req, res) => {
    const { title, description} = req.body

    // Validate title and description
    if (!title || title.trim() === "") {
        throw new ApiError(400, "Title is required")
    }

    if (!description || description.trim() === "") {
        throw new ApiError(400, "Description is required")
    }

    // Check for video file and thumbnail
    const videoFileLocalPath = req.files?.videoFile?.[0]?.path
    const thumbnailLocalPath = req.files?.thumbnail?.[0]?.path

    if (!videoFileLocalPath) {
        throw new ApiError(400, "Video file is required")
    }

    if (!thumbnailLocalPath) {
        throw new ApiError(400, "Thumbnail is required")
    }

    // Upload to cloudinary
    const videoFile = await uploadOnCloudinary(videoFileLocalPath)
    const thumbnail = await uploadOnCloudinary(thumbnailLocalPath)

    if (!videoFile) {
        throw new ApiError(500, "Failed to upload video file")
    }

    if (!thumbnail) {
        throw new ApiError(500, "Failed to upload thumbnail")
    }

    // Create video
    const video = await Video.create({
        videoFile: videoFile.url,
        thumbnail: thumbnail.url,
        title: title.trim(),
        description: description.trim(),
        duration: videoFile.duration || 0,
        owner: req.user._id
    })

    if (!video) {
        throw new ApiError(500, "Failed to create video")
    }

    return res
        .status(201)
        .json(
            new ApiResponse(201, video, "Video published successfully")
        )
})

const getVideoById = asyncHandler(async (req, res) => {
    const { videoId } = req.params

    // Validate videoId
    if (!isValidObjectId(videoId)) {
        throw new ApiError(400, "Invalid video ID")
    }

    // Get video with owner details
    const video = await Video.aggregate([
        {
            $match: {
                _id: new mongoose.Types.ObjectId(videoId)
            }
        },
        {
            $lookup: {
                from: "users",
                localField: "owner",
                foreignField: "_id",
                as: "owner",
                pipeline: [
                    {
                        $project: {
                            username: 1,
                            fullName: 1,
                            avatar: 1
                        }
                    }
                ]
            }
        },
        {
            $addFields: {
                owner: {
                    $first: "$owner"
                }
            }
        }
    ])

    if (!video || video.length === 0) {
        throw new ApiError(404, "Video not found")
    }

    // Increment views
    await Video.findByIdAndUpdate(videoId, {
        $inc: { views: 1 }
    })

    return res
        .status(200)
        .json(
            new ApiResponse(200, video[0], "Video fetched successfully")
        )
})

const updateVideo = asyncHandler(async (req, res) => {
    const { videoId } = req.params
    const { title, description } = req.body

    // Validate videoId
    if (!isValidObjectId(videoId)) {
        throw new ApiError(400, "Invalid video ID")
    }

    // At least one field should be provided
    if (!title && !description && !req.file) {
        throw new ApiError(400, "At least one field is required to update")
    }

    // Find video
    const video = await Video.findById(videoId)

    if (!video) {
        throw new ApiError(404, "Video not found")
    }

    // Verify ownership
    if (video.owner.toString() !== req.user._id.toString()) {
        throw new ApiError(403, "You are not authorized to update this video")
    }

    // Build update object
    const updateFields = {}

    if (title && title.trim() !== "") {
        updateFields.title = title.trim()
    }

    if (description && description.trim() !== "") {
        updateFields.description = description.trim()
    }

    // Handle thumbnail upload if provided
    if (req.file) {
        const thumbnailLocalPath = req.file.path
        const thumbnail = await uploadOnCloudinary(thumbnailLocalPath)

        if (!thumbnail) {
            throw new ApiError(500, "Failed to upload thumbnail")
        }

        updateFields.thumbnail = thumbnail.url
    }

    // Update video
    const updatedVideo = await Video.findByIdAndUpdate(
        videoId,
        {
            $set: updateFields
        },
        {
            new: true
        }
    )

    return res
        .status(200)
        .json(
            new ApiResponse(200, updatedVideo, "Video updated successfully")
        )
})

const deleteVideo = asyncHandler(async (req, res) => {
    const { videoId } = req.params

    // Validate videoId
    if (!isValidObjectId(videoId)) {
        throw new ApiError(400, "Invalid video ID")
    }

    // Find video
    const video = await Video.findById(videoId)

    if (!video) {
        throw new ApiError(404, "Video not found")
    }

    // Verify ownership
    if (video.owner.toString() !== req.user._id.toString()) {
        throw new ApiError(403, "You are not authorized to delete this video")
    }

    // Delete video
    await Video.findByIdAndDelete(videoId)

    return res
        .status(200)
        .json(
            new ApiResponse(200, {videoId}, "Video deleted successfully")
        )
})

const togglePublishStatus = asyncHandler(async (req, res) => {
    const { videoId } = req.params

    // Validate videoId
    if (!isValidObjectId(videoId)) {
        throw new ApiError(400, "Invalid video ID")
    }

    // Find video
    const video = await Video.findById(videoId)

    if (!video) {
        throw new ApiError(404, "Video not found")
    }

    // Verify ownership
    if (video.owner.toString() !== req.user._id.toString()) {
        throw new ApiError(403, "You are not authorized to update this video")
    }

    // Toggle publish status
    const updatedVideo = await Video.findByIdAndUpdate(
        videoId,
        {
            $set: {
                isPublished: !video.isPublished
            }
        },
        {
            new: true
        }
    )

    return res
        .status(200)
        .json(
            new ApiResponse(200, updatedVideo, `Video ${updatedVideo.isPublished ? 'published' : 'unpublished'} successfully`)
        )
})

export {
    getAllVideos,
    publishAVideo,
    getVideoById,
    updateVideo,
    deleteVideo,
    togglePublishStatus
}
