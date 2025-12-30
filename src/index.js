import { app } from "./app.js";
import CONNECT_DB from "./db/index.js";
import dotenv from "dotenv";

dotenv.config({
    path : './.env'
})


CONNECT_DB().then(
    ()=>{
        app.on("error",(err)=>{
        console.log("ERROR :-",err)
        throw error
    })
    app.listen(process.env.PORT || 800, ()=>{
        console.log(`Server is running on the port :- ${process.env.PORT}`)
    })
    }
).catch((err)=>{
    console.log("DB connection failed",err);
})

console.log("App started");