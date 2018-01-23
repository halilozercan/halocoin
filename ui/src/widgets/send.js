import React, { Component } from 'react';
import {axiosInstance} from '../tools.js';
import {Card, CardActions, CardHeader, CardText} from 'material-ui/Card';
import RaisedButton from 'material-ui/RaisedButton';
import TextField from 'material-ui/TextField';
import Avatar from 'material-ui/Avatar';
import FontIcon from 'material-ui/FontIcon';
import {yellow800} from 'material-ui/styles/colors';

class Send extends Component {

  constructor(props) {
    super(props);
    this.state = {
      "address": '',
      "amount": '',
      "password": ''
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
    if(this.state.password === '' || this.state.address === '' || this.state.amount === '') {
      this.props.notify('All fields must be filled', 'error');
      return;
    }
    let data = new FormData();
    data.append('address', this.state.address);
    data.append('password', this.state.password);
    data.append('amount', this.state.amount);

    axiosInstance.post('/send', data)
      .then((response) => {
        if(response.data.success)
          this.props.notify('Your transaction is successfully added to the pool', 'success');
        else
          this.props.notify(response.data.message, 'error');
      })
      .catch((error) => {
        this.props.notify('Something is wrong. Transaction failed!', 'error');
      });
    this.setState({
      'address': '',
      'amount': '',
      'password': ''
    })
  }

  render() {
    return (
      <Card style={{"margin":16}}>
        <CardHeader
          avatar={<Avatar backgroundColor={yellow800} icon={<FontIcon className="material-icons">credit_card</FontIcon>} />}
          title="Send coins"
          subtitle="Make a transaction"
        />
        <CardText>
          <form onSubmit={this.onSubmit}>
            <TextField
              fullWidth={true}
              floatingLabelText="Address"
              name="address"
              value={this.state.address}
              onChange={this.onChange}
            />
            <TextField
              fullWidth={true}
              floatingLabelText="Amount"
              name="amount"
              value={this.state.amount}
              onChange={this.onChange}
            />
            <TextField
              fullWidth={true}
              floatingLabelText="Password"
              name="password"
              type="password"
              value={this.state.password}
              onChange={this.onChange}
            />
          </form>
        </CardText>
        <CardActions align='right'>
          <RaisedButton label="Send" primary={true} onClick={this.onSubmit} />
        </CardActions>
      </Card>
    );
  }
}

export default Send;
