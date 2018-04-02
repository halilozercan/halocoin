import React, { Component } from 'react';
import {axiosInstance} from '../tools.js';
import {Card, CardActions, CardHeader, CardText} from 'material-ui/Card';
import RaisedButton from 'material-ui/RaisedButton';
import TextField from 'material-ui/TextField';

class NewWalletForm extends Component {

  constructor(props) {
    super(props);
    this.state = {
      "name": '',
      "password": '',
      "password2": ''
    }
  }

  onChange = (e) => {
    // Because we named the inputs to match their corresponding values in state, it's
    // super easy to update the state
    const state = this.state
    state[e.target.name] = e.target.value;
    console.log(state);
    this.setState(state);
  }

  onSubmit = (e) => {
    e.preventDefault();
    if(this.state.password === '' || this.state.name === '') {
      this.props.notify('Wallet name or password cannot be empty', 'error');
      return;
    }
    else if(this.state.password !== this.state.password2) {
      this.props.notify('Passwords must match', 'error');
      return;
    }
    let data = new FormData();
    data.append('wallet_name', this.state.name);
    data.append('password', this.state.password);
    data.append('login', true);

    axiosInstance.post('/wallet/new', data)
      .then((response) => {
        this.props.notify('Succesfully created the wallet ' + response.data.name, 'success');
        this.props.refresh();
      });
  }

  render() {
    return (
      <Card style={{"margin":16}}>
        <CardHeader
          title="New Wallet"
          subtitle="Create a new wallet to start Coinami"
        />
        <CardText>
          <form onSubmit={this.onSubmit}>
            <TextField
              fullWidth={true}
              floatingLabelText="Name"
              name="name"
              onChange={this.onChange}
            />
            <TextField
              fullWidth={true}
              floatingLabelText="Password"
              name="password"
              type="password"
              onChange={this.onChange}
            />
            <TextField
              fullWidth={true}
              floatingLabelText="Password(Again)"
              name="password2"
              type="password"
              onChange={this.onChange}
            />
          </form>
        </CardText>
        <CardActions align='right'>
          <RaisedButton label="Start" primary={true} onClick={this.onSubmit} />
        </CardActions>
      </Card>
    );
  }
}

export default NewWalletForm;
