import CONNECT_DB from "./db/index.js";
import dotenv from "dotenv";

dotenv.config({
    path : './.env'
})


CONNECT_DB()

console.log("App started");