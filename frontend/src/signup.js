import { useState } from "react";

function Signup() {

    const [email, setEmail] =
        useState("");

    const [password, setPassword] =
        useState("");

    const signup = async () => {

        await fetch(
            "/api/signup",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    email,
                    password
                })
            }
        );

        alert("Account created");
    };

    return (

        <div>

            <h1>Signup</h1>

            <input
                onChange={(e) =>
                    setEmail(e.target.value)}
            />

            <input
                type="password"
                onChange={(e) =>
                    setPassword(e.target.value)}
            />

            <button onClick={signup}>
                Signup
            </button>

        </div>
    );
}

export default Signup;