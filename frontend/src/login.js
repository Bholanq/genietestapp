import { useState } from "react";

function Login() {

    const [email, setEmail] = useState("");

    const [password, setPassword] =
        useState("");

    const login = async () => {

        const response = await fetch(
            "/api/login",
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

        const data =
            await response.json();

        localStorage.setItem(
            "token",
            data.token
        );

        window.location = "/dashboard";
    };

    return (

        <div>

            <h1>Login</h1>

            <input
                placeholder="Email"
                onChange={(e) =>
                    setEmail(e.target.value)}
            />

            <input
                type="password"
                placeholder="Password"
                onChange={(e) =>
                    setPassword(e.target.value)}
            />

            <button onClick={login}>
                Login
            </button>

        </div>
    );
}

export default Login;