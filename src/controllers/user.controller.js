import { asyncHandler } from "../utils/asyncHandler.js";
import { ApiError } from "../utils/ApiError.js";
import { User } from "../models/user.model.js";
import { upload } from "../middlewares/multer.middleware.js";
import { uploadOnCloudinary } from "../utils/cloudinary.js";
import { ApiResponse } from "../utils/ApiResponse.js";


const registerUser = asyncHandler(async(req,res)=>{

    //get user details from the frontend
    //validate all the fields from the req
    //check user with same credential doesnt exist
    //check for images, check for avatar
    //upload the files on cludinary, avatar(as ti was required field)
    //create user object  - entry in db
    //remove the password and refresh token field from response
    //check for user creation
    //return the response

    const {email,password, fullName, username} = req.body
    console.log("email",email)

    if([email, password, fullName, username].some((fields)=>{

            fields?.trim()===""
    })){
        throw new ApiError(400, "All fields are required")
    }

    const existedUser = await User.findOne(
        {$or:[{ email }, { username }]}
    )

    if(existedUser){
        throw new ApiError(409, "User with email or username already exists")
    }

    const avatarLocalPath = req.files?.avatar[0]?.path
    let coverImageLocalPath;

    if(req.files&&Array.isArray(req.files.coverImage)&&req.files.coverImage.length>0){
        coverImageLocalPath = req.files?.coverImage[0]?.path
    }

    if(!avatarLocalPath){
        throw new ApiError(400, "Avatar file is required")
    }

    const avatar = await uploadOnCloudinary(avatarLocalPath)
    const coverImage = await uploadOnCloudinary(coverImageLocalPath)

    if(!avatar){
        throw new ApiError(500, "Something went wrong while uploading the files on cloudinary")
    }

    const user = await User.create({
        fullName,
        avatar: avatar.url,
        coverImage: coverImage?.url || "",
        email,
        password,
        username: username.toLowerCase(),

    })

    const createdUser = await User.findById(user._id).select(
        "-password -refreshToken"
    )

    if(!createdUser){
        throw new ApiError(500, "Something went wrong while creating the user")
    }

    res.status(201).json(
        new ApiResponse(201, createdUser, "User registered Successfully")
    )
    
})

export {registerUser};