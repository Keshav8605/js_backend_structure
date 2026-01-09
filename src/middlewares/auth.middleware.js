import jwt from "jsonwebtoken";
import { asyncHandler } from "../utils/asyncHandler.js";
import { ApiError } from "../utils/ApiError";
import { User } from "../models/user.model.js";
import { ApiResponse } from "../utils/ApiResponse.js";


const verifyJWT = asyncHandler(async(req, res, next)=>{

        try {
            const token = req.cookies?.accessToken || req.header("Authorization")?.replace("Bearer ","")
    
            if(!token){
                throw new ApiError(401, "Unauthorised access")
            }
    
            const decodedToken =  jwt.verify(token, process.env.ACCESS_TOKEN_SECRET)
    
            const user = await User.findOne(decodedToken?._id).select("-password -refreshToken")
    
            if(!user){
                throw new ApiError(401, "Invalid access token")
            }
    
            req.user = user;
            next()
        } catch (error) {

            new ApiResponse(401, "Unauthorised access")
            
        }

})

export { verifyJWT }