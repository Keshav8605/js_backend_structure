import "dotenv/config";




import { app } from "./app.js";
import CONNECT_DB from "./db/index.js";



CONNECT_DB().then(
    ()=>{
        app.on("error",(err)=>{
        console.log("ERROR :-",err)
        throw err
    })
    app.listen(process.env.PORT || 8000, ()=>{
        console.log(`Server is running on the port :- ${process.env.PORT}`)
    })
    }
).catch((err)=>{
    console.log("DB connection failed",err);
})

console.log("App started");