import mongoose from "mongoose";
import { DB_NAME } from "../constants.js";


const CONNECT_DB = async ()=>{

    try {

       const connectionInstance = await mongoose.connect(`${process.env.MONGODB_URI}/${DB_NAME}`)
       console.log(`\n DB coneected successfully!! DB HOST :- ${connectionInstance.connection.host}`)
    
    } catch (error) {

        console.log("ERROR while connecting the database ",error)
        process.exit(1)
        
    }

};

export default CONNECT_DB;